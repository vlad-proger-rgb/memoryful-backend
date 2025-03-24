from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    Country,
    City,
    ChatModel,
)


async def init_db(db: AsyncSession):

    # countries and cities
    if not (await db.scalar(select(Country.id).limit(1))):
        united_states = Country(name="United States", code="US", cities=[
            City(name="New York"),
            City(name="Los Angeles"),
        ])
        ukraine = Country(name="Ukraine", code="UA", cities=[
            City(name="Kyiv"),
            City(name="Kharkiv"),
        ])
        poland = Country(name="Poland", code="PL", cities=[
            City(name="Warsaw"),
            City(name="Krakow"),
        ])
        germany = Country(name="Germany", code="DE", cities=[
            City(name="Berlin"),
            City(name="Düsseldorf"),
        ])

        db.add_all([united_states, ukraine, poland, germany])
        await db.commit()

    # chat models
    if not (await db.scalar(select(ChatModel.id).limit(1))):
        db.add_all([
            ChatModel(label="GPT-3.5", name="gpt-3.5-turbo"),
            ChatModel(label="GPT-4", name="gpt-4"),
        ])
        await db.commit()

