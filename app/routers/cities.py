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
    CityInDB as C,
)
from app.core.database import get_db
from app.models import Country, City


router = APIRouter(
    prefix="/cities",
    tags=["Cities"],
)


@router.get("/by-country/{country_id}", response_model=Msg[list[C]])
async def get_cities_by_country_id(
    db: Annotated[AsyncSession, Depends(get_db)],
    country_id: UUID,
    query: str | None = Query(None, description="Substring to search for in city name"),
    limit: int = Query(10, ge=1, le=100),
    offset: int = Query(0, ge=0),
) -> Msg[list[C]]:
    country = await db.get(Country, country_id)
    if not country:
        raise HTTPException(status_code=404, detail="Country not found")

    stmt = (
        select(City)
        .where(City.country_id == country_id)
        .limit(limit)
        .offset(offset)
    )

    if query:
        stmt = stmt.where(City.name.ilike(f"%{query}%"))

    result = await db.execute(stmt)
    cities = result.scalars().unique().all()

    return Msg(code=200, msg="Cities retrieved", data=cities)


@router.get("/{city_id}", response_model=Msg[C])
async def get_city_by_id(
    db: Annotated[AsyncSession, Depends(get_db)],
    city_id: UUID,
) -> Msg[C]:
    city = await db.get(City, city_id)
    if not city:
        raise HTTPException(status_code=404, detail="City not found")

    return Msg(code=200, msg="City retrieved", data=city)

