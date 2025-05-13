from typing import Annotated, Sequence
import datetime as dt
from uuid import UUID

from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession
from jose import jwt, JWTError
from fastapi import (
    APIRouter,
    HTTPException,
    Response,
    Header,
    Depends,
    Request,
)

from app.models import User, UserToken, Country, City
from app.tasks import send_email_task
from app.core.database import get_db
from app.core.enums import EmailTemplate
from app.core.config import redis
from app.core.utils import generate_activation_code
from app.core.deps import get_current_user

from app.core.security import (
    oauth2_scheme,
    create_and_store_tokens,
    verify_code_form,
    verify_refresh_token,
)
from app.core.settings import (
    ACCESS_SECRET_KEY,
    ALGORITHM,
    VERIFICATION_CODE_EXPIRE_MINUTES,
    RP_LOGIN_CODE,
    RP_BLACKLISTED_TOKEN,
    REFRESH_SECRET_KEY,
)
from app.schemas import (
    Msg,
    Email,
    Session,
    VerifyCodeForm,
    UserBase,
    UserInDB,
    Token,
    AuthResponse,
)


router = APIRouter(
    prefix="/auth",
    tags=["Auth"],
)


@router.get("/me", response_model=Msg[UserInDB])
async def get_me(
    current_user: Annotated[User, Depends(get_current_user(True))],
) -> Msg[UserInDB]:
    return Msg(code=200, msg="Current user retrieved", data=UserInDB.model_validate(current_user))


@router.post("/request-code", response_model=Msg[None])
async def request_code(email: Email) -> Msg[None]:
    print(f"AUTH POST /request-code {email.email=}")
    activation_code = generate_activation_code()

    await redis.setex(
        f"{RP_LOGIN_CODE}{email.email}",
        VERIFICATION_CODE_EXPIRE_MINUTES * 60,
        activation_code,
    )

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
    print(f"AUTH POST /verify-code {code_form=}")

    await verify_code_form(f"{RP_LOGIN_CODE}{code_form.email}", code_form)

    stmt = select(User).where(User.email == code_form.email)
    user: User | None = (await db.scalars(stmt)).one_or_none()

    is_new_user = False
    if not user:
        is_new_user = True
        user = User(email=code_form.email)
        db.add(user)
        await db.commit()
        await db.refresh(user)

    tokens = await create_and_store_tokens(db, user, request)
    if tokens.refresh_token:
        response.set_cookie(
            key="refresh_token",
            value=tokens.refresh_token,
            httponly=True,
            secure=True,
            samesite="lax",
        )

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
    authorization: str = Header(...),
) -> Msg[Token]:
    scheme, _, refresh_token = authorization.partition(" ")
    print(f"AUTH GET /refresh {scheme=}, {refresh_token=}")
    if scheme.lower() != "bearer":
        raise HTTPException(401, "Could not validate credentials (scheme not bearer)", {"WWW-Authenticate": "Bearer"})

    if not refresh_token:
        raise HTTPException(401, "No refresh token provided", {"WWW-Authenticate": "Bearer"})

    try:
        payload = jwt.decode(refresh_token, REFRESH_SECRET_KEY, algorithms=[ALGORITHM])
        if not (jti := payload.get("jti")):
            raise HTTPException(401, "Invalid token format", {"WWW-Authenticate": "Bearer"})

        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(401, "Invalid token format - missing user ID", {"WWW-Authenticate": "Bearer"})

    except JWTError:
        raise HTTPException(401, "Invalid token format", {"WWW-Authenticate": "Bearer"})

    token_db = await db.get(UserToken, jti)
    if not token_db:
        raise HTTPException(401, "Token not found", {"WWW-Authenticate": "Bearer"})

    if not verify_refresh_token(refresh_token, token_db.refresh_token_hash):
        raise HTTPException(401, "Invalid token", {"WWW-Authenticate": "Bearer"}) 

    if token_db.expires_at < dt.datetime.now(dt.UTC):
        await db.delete(token_db)
        await db.commit()
        raise HTTPException(401, "Token expired", {"WWW-Authenticate": "Bearer"})

    user = await db.get(User, token_db.user_id)
    if not user:
        await db.delete(token_db)
        await db.commit()
        raise HTTPException(401, "User not found", {"WWW-Authenticate": "Bearer"})

    if not user.is_enabled:
        await db.delete(token_db)
        await db.commit()
        raise HTTPException(401, "User is disabled", {"WWW-Authenticate": "Bearer"})

    if token_db.ip_address and request.client and request.client.host != token_db.ip_address:
        print(f"AUTH GET /refresh Warning: Token used from different IP: {token_db.ip_address} vs {request.client.host}")
        # Uncomment below to enforce IP validation
        # raise HTTPException(401, "Suspicious activity detected", {"WWW-Authenticate": "Bearer"})

    await db.delete(token_db)
    await db.commit()

    new_tokens = await create_and_store_tokens(db, user, request)

    return Msg(code=200, msg="Token refreshed", data=new_tokens)


@router.put("/me", response_model=Msg[None])
async def update_me(
    db: Annotated[AsyncSession, Depends(get_db)],
    user_id: Annotated[UUID, Depends(get_current_user())],
    new_user: UserBase,
) -> Msg[None]:
    if new_user.country_id:
        country = await db.get(Country, new_user.country_id)
        if not country:
            raise HTTPException(404, "Country not found")

    if new_user.city_id:
        city = await db.get(City, new_user.city_id)
        if not city:
            raise HTTPException(404, "City not found")

    stmt = (
        update(User)
        .where(User.id == user_id)
        .values(**new_user.model_dump(exclude_unset=True))
    )
    await db.execute(stmt)
    await db.commit()
    return Msg(code=200, msg="User was updated")


@router.get("/logout", response_model=Msg[None])
async def logout(
    db: Annotated[AsyncSession, Depends(get_db)],
    token: Annotated[str, Depends(oauth2_scheme)],
    request: Request,
) -> Msg[None]:
    try:
        payload = jwt.decode(token, ACCESS_SECRET_KEY, algorithms=ALGORITHM)
        print(f"UTILS logout {payload=}")
        user_id = payload.get("sub")
        jti = payload.get("jti")
        exp_time = payload.get("exp")

        if jti and exp_time:
            ttl = max(0, exp_time - int(dt.datetime.now(dt.UTC).timestamp()))
            await redis.setex(f"{RP_BLACKLISTED_TOKEN}{jti}", ttl, "true")

        stmt = delete(UserToken).where(
            UserToken.user_id == user_id,
            UserToken.user_agent == request.headers.get("User-Agent"),
            UserToken.ip_address == (request.client.host if request.client else None),
        )
        await db.execute(stmt)
        await db.commit()

    except Exception as e:
        print(f"UTILS Error during logout: {e}")

    return Msg(code=200, msg="Logout was successful")


@router.post("/logout-all", response_model=Msg[None])
async def logout_all(
    db: Annotated[AsyncSession, Depends(get_db)],
    user_id: Annotated[UUID, Depends(get_current_user())],
) -> Msg[None]:
    stmt = delete(UserToken).where(UserToken.user_id == user_id)
    await db.execute(stmt)
    await db.commit()
    return Msg(code=200, msg="All sessions revoked")


@router.get("/sessions", response_model=Msg[Sequence[Session]])
async def list_sessions(
    db: Annotated[AsyncSession, Depends(get_db)],
    user_id: Annotated[UUID, Depends(get_current_user())],
) -> Msg[Sequence[Session]]:
    stmt = select(UserToken).where(UserToken.user_id == user_id)
    result = await db.execute(stmt)
    tokens: Sequence[UserToken] = result.scalars().all()

    sessions = [
        Session(
            id=token.id,
            ip_address=token.ip_address,
            user_agent=token.user_agent,
            created_at=token.created_at,
            expires_at=token.expires_at,
        )
        for token in tokens
    ]

    return Msg(code=200, msg="Sessions retrieved", data=sessions)


@router.delete("/sessions/{session_id}", response_model=Msg[None])
async def revoke_session(
    db: Annotated[AsyncSession, Depends(get_db)],
    user_id: Annotated[UUID, Depends(get_current_user())],
    session_id: UUID,
) -> Msg[None]:
    stmt = select(UserToken).where(
        UserToken.id == session_id,
        UserToken.user_id == user_id,
    )
    result = await db.execute(stmt)
    token = result.scalar_one_or_none()

    if not token:
        raise HTTPException(404, "Session not found")

    await db.delete(token)
    await db.commit()

    return Msg(code=200, msg="Session revoked")
