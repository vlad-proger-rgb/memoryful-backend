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
from sqlalchemy.orm import selectinload
from app.schemas import (
    Msg,
    CityInDB,
    CityDetail,
)
from app.core.database import get_db
from app.models import Country, City


router = APIRouter(
    prefix="/cities",
    tags=["Cities"],
)


@router.get("/by-country/{country_id}", response_model=Msg[list[CityInDB]])
async def get_cities_by_country_id(
    db: Annotated[AsyncSession, Depends(get_db)],
    country_id: UUID,
    query: str | None = Query(None, description="Substring to search for in city name"),
    limit: int = Query(10, ge=1, le=100),
    offset: int = Query(0, ge=0),
) -> Msg[list[CityInDB]]:
    country = await db.get(Country, country_id)
    if not country:
        raise HTTPException(404, "Country not found")

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

    return Msg(code=200, msg="Cities retrieved", data=[CityInDB.model_validate(c) for c in cities])


@router.get("/{city_id}", response_model=Msg[CityDetail])
async def get_city_by_id(
    db: Annotated[AsyncSession, Depends(get_db)],
    city_id: UUID,
) -> Msg[CityDetail]:
    city = await db.get(City, city_id, options=[selectinload(City.country)])
    if not city:
        raise HTTPException(404, "City not found")

    return Msg(code=200, msg="City retrieved", data=CityDetail.model_validate(city))

