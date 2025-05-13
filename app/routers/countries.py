from typing import Annotated
from uuid import UUID

from fastapi import (
    APIRouter,
    HTTPException,
    Depends,
    Query,
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas import (
    Msg,
    CountryInDB as C,
)
from app.core.database import get_db
from app.models import Country


router = APIRouter(
    prefix="/countries",
    tags=["Countries"],
)


@router.get("/all/", response_model=Msg[list[C]])
async def get_countries(
    db: Annotated[AsyncSession, Depends(get_db)],
    query: str | None = Query(None, description="Substring to search for in country name"),
    limit: int = Query(10, ge=1, le=100),
    offset: int = Query(0, ge=0),
) -> Msg[list[C]]:
    stmt = (
        select(Country)
        .limit(limit)
        .offset(offset)
    )

    if query:
        stmt = stmt.where(Country.name.ilike(f"%{query}%"))

    result = await db.execute(stmt)
    countries = result.scalars().unique().all()

    return Msg(code=200, msg="Countries retrieved", data=[C.model_validate(c) for c in countries])


@router.get("/{country_id}", response_model=Msg[C])
async def get_country_by_id(
    db: Annotated[AsyncSession, Depends(get_db)],
    country_id: UUID,
) -> Msg[C]:
    country = await db.get(Country, country_id)
    if not country:
        raise HTTPException(status_code=404, detail="Country not found")

    return Msg(code=200, msg="Country retrieved", data=C.model_validate(country))

