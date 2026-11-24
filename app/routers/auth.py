import datetime as dt
import logging
import secrets
from collections.abc import Sequence
from typing import Annotated
from uuid import UUID

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Cookie,
    Depends,
    Header,
    HTTPException,
    Request,
    Response,
)
from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.constants import (
    CACHE_TTL_USER_DATA,
    GOOGLE_NONCE_EXPIRE_MINUTES,
    VERIFICATION_CODE_EXPIRE_MINUTES,
)
from app.core.cache import cached, clear_cache
from app.core.config import redis
from app.core.database import get_db
from app.core.deps import StorageServiceDep, get_current_user, get_session_id
from app.core.security import (
    InvalidTokenError,
    oauth2_scheme,
    read_token,
    unauthorized,
    verify_code_form,
    verify_google_id_token,
    verify_refresh_token,
)
from app.core.sessions import (
    access_token_only,
    blacklist_session,
    issue_session,
    rotate_session_tokens,
    set_refresh_cookie,
    within_reuse_grace,
)
from app.core.settings import get_settings
from app.core.storage.utils import orphaned_keys
from app.core.utils import generate_activation_code
from app.enums import CacheNamespace, EmailTemplate, RedisPrefix, TokenType
from app.models import City, Country, User, UserToken
from app.schemas import (
    AuthResponse,
    Email,
    GoogleCredential,
    GoogleNonce,
    Msg,
    Session,
    Token,
    UserBase,
    UserInDB,
    VerifyCodeForm,
)
from app.tasks import send_email_task

settings = get_settings()
logger = logging.getLogger(__name__)


router = APIRouter(
    prefix="/auth",
    tags=["Auth"],
)


@router.get("/me", response_model=Msg[UserInDB])
@cached(expire=CACHE_TTL_USER_DATA, namespace=CacheNamespace.users)
async def get_me(
    db: Annotated[AsyncSession, Depends(get_db)],
    user_id: Annotated[UUID, Depends(get_current_user())],
) -> Msg[UserInDB]:
    current_user = await db.get(
        User, user_id, options=[selectinload(User.country), selectinload(User.city)]
    )
    if not current_user:
        raise HTTPException(404, "User not found")

    return Msg(code=200, msg="Current user retrieved", data=UserInDB.model_validate(current_user))


@router.post("/request-code", response_model=Msg[None])
async def request_code(email: Email) -> Msg[None]:
    """
    A pending code is resent rather than replaced, so a delayed email still works
    """

    if not settings.is_trusted_email(email.email):
        new_code = generate_activation_code()
        pending = await redis.set(
            f"{RedisPrefix.login_code}{email.email}",
            new_code,
            ex=VERIFICATION_CODE_EXPIRE_MINUTES * 60,
            nx=True,
            get=True,
        )
        activation_code = str(pending) if pending else new_code

        send_email_task.delay(
            email_type=EmailTemplate.CONFIRMATION_CODE,
            recipients=[email.email],
            body={
                "subject": "Login Code",
                "code": activation_code,
            },
        )

    return Msg(code=200, msg="Code was sent")


@router.post("/verify-code", response_model=Msg[AuthResponse])
async def verify_code(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    response: Response,
    code_form: VerifyCodeForm,
) -> Msg[AuthResponse]:
    if not settings.is_trusted_email(code_form.email):
        await verify_code_form(f"{RedisPrefix.login_code}{code_form.email}", code_form)

    stmt = select(User).where(User.email == code_form.email)
    user: User | None = (await db.scalars(stmt)).one_or_none()

    is_new_user = False
    if not user:
        is_new_user = True
        user = User(email=code_form.email)
        db.add(user)
        await db.commit()
        await db.refresh(user)

    elif not user.is_enabled:
        raise unauthorized("User is disabled")

    tokens = await issue_session(db, user, request, response)

    return Msg(
        code=201,
        msg="Authentication was successful",
        data=AuthResponse(
            tokens=tokens,
            is_new_user=is_new_user,
            user_id=user.id,
        ),
    )


@router.post("/google/nonce", response_model=Msg[GoogleNonce])
async def google_nonce() -> Msg[GoogleNonce]:
    nonce = secrets.token_urlsafe(32)
    await redis.setex(f"{RedisPrefix.google_nonce}{nonce}", GOOGLE_NONCE_EXPIRE_MINUTES * 60, "1")

    return Msg(code=200, msg="Nonce issued", data=GoogleNonce(nonce=nonce))


@router.post("/google", response_model=Msg[AuthResponse])
async def google_sign_in(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    response: Response,
    credential: GoogleCredential,
) -> Msg[AuthResponse]:
    claims = await verify_google_id_token(credential.credential)
    email = str(claims["email"]).strip().lower()
    google_sub = str(claims["sub"])

    # DELETE returns 1 only for whoever gets there first, so a replay loses the race.
    nonce = claims.get("nonce")
    if not nonce or not await redis.delete(f"{RedisPrefix.google_nonce}{nonce}"):
        raise unauthorized("Invalid Google credential")

    # sub before email: the reverse order forks the account when a Google address changes.
    user: User | None = await db.scalar(select(User).where(User.google_sub == google_sub))
    linked_by_sub = user is not None

    if user is None:
        user = await db.scalar(select(User).where(User.email == email))

    is_new_user = False
    if user is None:
        is_new_user = True
        user = User(
            email=email,
            google_sub=google_sub,
            first_name=claims.get("given_name"),
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
    else:
        if not user.is_enabled:
            raise unauthorized("User is disabled")

        if linked_by_sub and user.email != email:
            conflict = await db.scalar(select(User.id).where(User.email == email))
            if conflict is not None:
                raise HTTPException(
                    409,
                    "That email address already belongs to another account",
                )
            user.email = email

        user.google_sub = google_sub
        await db.commit()
        await db.refresh(user)
        await clear_cache(CacheNamespace.users, user.id)

    tokens = await issue_session(db, user, request, response)

    return Msg(
        code=201,
        msg="Authentication was successful",
        data=AuthResponse(
            tokens=tokens,
            is_new_user=is_new_user,
            user_id=user.id,
        ),
    )


@router.get("/refresh", response_model=Msg[Token])
async def refresh_token(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    response: Response,
    refresh_token_cookie: str | None = Cookie(default=None, alias="refresh_token"),
    authorization: str | None = Header(default=None),
) -> Msg[Token]:
    refresh_token: str | None = refresh_token_cookie
    scheme = ""
    if not refresh_token and authorization:
        scheme, _, candidate = authorization.partition(" ")
        if scheme.lower() == "bearer" and candidate:
            refresh_token = candidate

    if not refresh_token:
        raise unauthorized("No refresh token provided")

    try:
        claims = read_token(refresh_token, TokenType.refresh)
    except InvalidTokenError as e:
        raise unauthorized("Invalid token format") from e

    # The lock makes a concurrent refresh wait and then see this one's rotation.
    session = await db.scalar(
        select(UserToken)
        .where(UserToken.id == claims.session_id, UserToken.user_id == claims.user_id)
        .with_for_update()
    )
    if not session:
        raise unauthorized("Session not found")

    if session.expires_at < dt.datetime.now(dt.UTC):
        await db.delete(session)
        await db.commit()
        raise unauthorized("Token expired")

    user = await db.get(User, session.user_id)
    if not user:
        await db.delete(session)
        await db.commit()
        raise unauthorized("User not found")

    if not user.is_enabled:
        await db.delete(session)
        await db.commit()
        raise unauthorized("User is disabled")

    if not verify_refresh_token(refresh_token, session.refresh_token_hash):
        if within_reuse_grace(session, refresh_token):
            return Msg(code=200, msg="Token refreshed", data=access_token_only(session))

        logger.warning(
            "Refresh token reused for session %s of user %s; revoking it", session.id, user.id
        )
        await blacklist_session(session.id)
        await db.delete(session)
        await db.commit()
        raise unauthorized("Invalid token")

    if session.ip_address and request.client and request.client.host != session.ip_address:
        logger.warning(
            "Refresh token for session %s of user %s used from a new IP", session.id, user.id
        )

    tokens = await rotate_session_tokens(db, session, request)
    return Msg(code=200, msg="Token refreshed", data=set_refresh_cookie(response, tokens))


@router.put("/me", response_model=Msg[None])
async def update_me(
    db: Annotated[AsyncSession, Depends(get_db)],
    user_id: Annotated[UUID, Depends(get_current_user())],
    new_user: UserBase,
    storage_service: StorageServiceDep,
    background_tasks: BackgroundTasks,
) -> Msg[None]:
    country = None
    city = None

    if new_user.country and new_user.country.id:
        country = await db.get(Country, new_user.country.id)
        if not country:
            raise HTTPException(404, "Country not found")

    if new_user.city and new_user.city.id:
        city = await db.get(City, new_user.city.id)
        if not city:
            raise HTTPException(404, "City not found")

    if city and country and city.country_id != country.id:
        raise HTTPException(400, "Selected city does not belong to selected country")

    update_data = new_user.model_dump(exclude_unset=True)

    previous_photo = await db.scalar(select(User.photo).where(User.id == user_id))
    # An unsent field keeps its current value, so it must not count as orphaned.
    orphaned = orphaned_keys(previous_photo, update_data.get("photo", previous_photo))

    update_data.pop("country", None)
    update_data.pop("city", None)

    if city:
        update_data["city_id"] = city.id
        if country:
            update_data["country_id"] = country.id
        else:
            update_data["country_id"] = city.country_id
    elif country:
        update_data["country_id"] = country.id

    stmt = (
        update(User)
        .where(User.id == user_id)
        .values(**update_data)
    )  # fmt: skip
    await db.execute(stmt)
    await db.commit()

    await clear_cache(CacheNamespace.users, user_id)
    await redis.delete(f"{RedisPrefix.ai_context}{user_id}")
    background_tasks.add_task(storage_service.delete_objects, user_id, orphaned)
    return Msg(code=200, msg="User was updated")


@router.get("/logout", response_model=Msg[None])
async def logout(
    db: Annotated[AsyncSession, Depends(get_db)],
    token: Annotated[str, Depends(oauth2_scheme)],
    response: Response,
) -> Msg[None]:
    try:
        claims = read_token(token, TokenType.access)
        await blacklist_session(claims.session_id)
        await db.execute(
            delete(UserToken).where(
                UserToken.id == claims.session_id, UserToken.user_id == claims.user_id
            )
        )
        await db.commit()

    except Exception as e:
        logger.warning("Logout cleanup failed: %s", type(e).__name__)

    response.delete_cookie(key="refresh_token", path="/")

    return Msg(code=200, msg="Logout was successful")


@router.post("/logout-all", response_model=Msg[None])
async def logout_all(
    db: Annotated[AsyncSession, Depends(get_db)],
    user_id: Annotated[UUID, Depends(get_current_user())],
) -> Msg[None]:
    session_ids = (await db.scalars(select(UserToken.id).where(UserToken.user_id == user_id))).all()
    for session_id in session_ids:
        await blacklist_session(session_id)

    await db.execute(delete(UserToken).where(UserToken.user_id == user_id))
    await db.commit()
    return Msg(code=200, msg="All sessions revoked")


@router.get("/sessions", response_model=Msg[Sequence[Session]])
async def list_sessions(
    db: Annotated[AsyncSession, Depends(get_db)],
    user_id: Annotated[UUID, Depends(get_current_user())],
    current_session_id: Annotated[UUID, Depends(get_session_id)],
) -> Msg[Sequence[Session]]:
    rows = (await db.scalars(select(UserToken).where(UserToken.user_id == user_id))).all()
    sessions = [
        Session(
            id=row.id,
            ip_address=row.ip_address,
            user_agent=row.user_agent,
            created_at=row.created_at,
            expires_at=row.expires_at,
            is_current=row.id == current_session_id,
        )
        for row in rows
    ]
    return Msg(code=200, msg="Sessions retrieved", data=sessions)


@router.delete("/sessions/{session_id}", response_model=Msg[None])
async def revoke_session(
    db: Annotated[AsyncSession, Depends(get_db)],
    user_id: Annotated[UUID, Depends(get_current_user())],
    session_id: UUID,
) -> Msg[None]:
    session = await db.scalar(
        select(UserToken).where(UserToken.id == session_id, UserToken.user_id == user_id)
    )
    if not session:
        raise HTTPException(404, "Session not found")

    await blacklist_session(session.id)
    await db.delete(session)
    await db.commit()

    return Msg(code=200, msg="Session revoked")
