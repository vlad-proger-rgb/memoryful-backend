import random
import datetime as dt

from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.settings import MAIL_FROM
from app.enums.font_awesome import IconStyle
from app.schemas.font_awesome import FAIcon
from app.models import (
    Country,
    City,
    ChatModel,
    User,
    Tag,
    TrackableType,
    TrackableItem,
    TrackableProgress,
    Day,
    Month,
)


async def init_db(db: AsyncSession) -> None:

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

    # user
    if not (await db.scalar(select(User.id).limit(1))):
        country = (await db.scalars(select(Country).where(Country.name == "United States"))).one()
        city = (await db.scalars(select(City).where(City.name == "New York"))).one()
        user = User(
            country_id=country.id,
            city_id=city.id,
            email=MAIL_FROM,
            is_enabled=True,
            first_name="John",
            last_name="Doe",
            age=30,
            bio="Some bio",
            job_title="Python developer",
            photo="me.jpg",
        )
        db.add(user)
        await db.commit()

    # tags
    if not (await db.scalar(select(Tag.id).limit(1))):
        user_id = (await db.scalars(select(User.id).limit(1))).one()
        db.add_all([
            Tag(name="Work", icon="work", color="red", user_id=user_id),
            Tag(name="Travel", icon="travel", color="blue", user_id=user_id),
            Tag(name="Study", icon="study", color="green", user_id=user_id),
        ])
        await db.commit()

    # trackable types
    if not (await db.scalar(select(TrackableType.id).limit(1))):
        db.add_all([
            TrackableType(name="learning", description="Learning", value_type="minutes", icon=FAIcon(name="book").model_dump()),
            TrackableType(name="activity", description="Activity", value_type="km", icon=FAIcon(name="person-walking").model_dump()),
        ])
        await db.commit()

    # trackable items
    if not (await db.scalar(select(TrackableItem.id).limit(1))):
        user_id = (await db.scalars(select(User.id).limit(1))).one()
        trackable_types = (await db.scalars(select(TrackableType))).all()
        db.add_all([
            TrackableItem(
                title="Python",
                description="Python programming language",
                icon=FAIcon(name="python", style=IconStyle.fab).model_dump(),
                user_id=user_id,
                type=trackable_types[0],
            ),
            TrackableItem(
                title="JavaScript",
                description="JavaScript programming language",
                icon=FAIcon(name="js", style=IconStyle.fab).model_dump(),
                user_id=user_id,
                type=trackable_types[0],
            ),
            TrackableItem(
                title="Running",
                description="Morning run",
                icon=FAIcon(name="person-walking", style=IconStyle.fas).model_dump(),
                user_id=user_id,
                type=trackable_types[1],
            ),
        ])
        await db.commit()

    # months
    if not (await db.scalar(select(Month.month).limit(1))):
        user_id = (await db.scalars(select(User.id).limit(1))).one()
        today = dt.date.today()
        db.add_all([
            Month(
                user_id=user_id,
                month=today.month - 1,
                year=today.year,
                description="The previous month",
                background_image="month1.jpg",
                top_day_timestamp=int(dt.datetime(today.year, today.month - 1, 1).timestamp())
            ),
            Month(
                user_id=user_id,
                month=today.month,
                year=today.year,
                description="The current month",
                background_image="month2.jpg",
                top_day_timestamp=int(dt.datetime(today.year, today.month, 2).timestamp())
            ),
            Month(
                user_id=user_id,
                month=today.month + 1,
                year=today.year,
                description="The next month",
                background_image="month3.jpg",
                top_day_timestamp=int(dt.datetime(today.year, today.month + 1, 3).timestamp())
            ),
        ])
        await db.commit()

    # days
    if not (await db.scalar(select(Day.timestamp).limit(1))):
        user_id = (await db.scalars(select(User.id).limit(1))).one()
        cities = (await db.scalars(select(City))).all()
        tags = (await db.scalars(select(Tag).where(Tag.user_id == user_id))).all()
        trackable_items = (await db.scalars(select(TrackableItem).options(selectinload(TrackableItem.type)))).all()

        today = dt.date.today()
        print(f"\n=== DEBUG: Today's date: {today}")

        # First day of previous month
        first_day = (today.replace(day=1) - dt.timedelta(days=1)).replace(day=1)
        # Last day of current month
        last_day = (today.replace(day=28) + dt.timedelta(days=4)).replace(day=1) - dt.timedelta(days=1)

        print(f"DEBUG: Date range - First day: {first_day}, Last day: {last_day}")
        print(f"DEBUG: Will skip dates after: {today}")

        # For testing - uncomment to generate more days
        # first_day = today - dt.timedelta(days=30)  # Last 30 days
        # last_day = today + dt.timedelta(days=30)   # Next 30 days

        days = []
        day_images = [
            "day1.jpg", "day2.jpg", "day3.jpg", "day4.jpg", "day5.jpg",
            "krakow.jpg", "kyiv.jpg", "kyiv2.jpg",
        ]

        # Generate days for the 3-month period
        current_date = first_day
        while current_date <= last_day:
            # Skip if it's a future date (beyond today)
            if current_date > today:
                print(f"DEBUG: Skipping future date: {current_date}")
                current_date += dt.timedelta(days=1)
                continue

            print(f"DEBUG: Processing date: {current_date}")

            timestamp = int(dt.datetime.combine(current_date, dt.time()).timestamp())

            # Random values for the day
            is_weekend = current_date.weekday() >= 5
            is_weekday = not is_weekend

            # Base steps: 2000-3000 on weekdays, 3000-5000 on weekends
            base_steps = random.randint(2000, 3000) if is_weekday else random.randint(3000, 5000)
            # Add some variation
            steps = max(1000, base_steps + random.randint(-500, 2000))

            # Random city
            city = random.choice(cities)

            # Random tags (1-3 tags per day, 30% chance for no tags)
            day_tags = []
            if random.random() > 0.3:  # 70% chance to have at least one tag
                num_tags = random.randint(1, min(3, len(tags)))
                day_tags = random.sample(tags, num_tags)

            # Random trackable items (0-3 items per day, 40% chance for none)
            day_trackable_items = []
            if trackable_items and random.random() > 0.4:  # 60% chance to have at least one item
                num_items = random.randint(1, min(3, len(trackable_items)))
                day_trackable_items = random.sample(trackable_items, num_items)

            # Create trackable progresses for the day
            trackable_progresses = []
            for item in day_trackable_items:
                if item.type.name == "learning":
                    value = random.randint(15, 180)  # 15-180 minutes
                elif item.type.name == "activity":
                    value = random.randint(1, 10)  # 1-10 km
                else:  # HABIT
                    value = 1  # Binary completion

                trackable_progresses.append(TrackableProgress(
                    user_id=user_id,
                    trackable_item_id=item.id,
                    timestamp=timestamp,
                    value=value,
                ))

            # Create day description based on the day of week and random activities
            activities = [
                "Worked on the project", "Met with friends", "Went for a walk", 
                "Visited a cafe", "Had a productive day", "Relaxed at home",
                "Explored the city", "Had a meeting", "Worked out"
            ]

            # Create day content with more details
            day_content = f"""**Day Summary - {current_date.strftime('%A, %B %d, %Y')}**. Today was a {'great' if random.random() > 0.3 else 'good'} day."""

            if day_trackable_items:
                day_content += "I made progress on "
                day_content += ", ".join([item.title for item in day_trackable_items])
                day_content += ". "

                # Add progress details
                for progress in trackable_progresses:
                    matching_items = [i for i in day_trackable_items if i.id == progress.trackable_item_id]
                    if matching_items:
                        item = matching_items[0]
                        if item.type.name == "learning":
                            day_content += f"Spent {progress.value} minutes on {item.title}. "
                        elif item.type.name == "activity":
                            day_content += f"Did {progress.value}km of {item.title}. "
                        else:  # HABIT
                            day_content += f"Completed {item.title}. "

            if day_tags:
                day_content += f"I was focused on {', '.join([tag.name for tag in day_tags])}."

            day_content += f" Walked {steps} steps today."

            # Add some random notes
            notes = [
                "The weather was nice today.",
                "Tried a new coffee place in the neighborhood.",
                "Had a productive coding session.",
                "Read an interesting article about AI.",
                "Need to follow up on some emails.",
                "Planning the next project phase.",
                "Learned some new techniques.",
                "Had a good workout session.",
                "Implemented this random days generator.",
            ]

            day_content += f"{random.choice(notes)}"

            # Create the day
            day = Day(
                timestamp=timestamp,
                user_id=user_id,
                city_id=city.id,
                description=random.choice(activities),
                content=day_content,
                steps=steps,
                starred=random.random() > 0.9,  # 10% chance to be starred
                main_image=random.choice(day_images) if random.random() > 0.3 else None,  # 70% chance to have an image
                tags=day_tags,
                trackable_progresses=trackable_progresses,
            )

            days.append(day)
            current_date += dt.timedelta(days=1)

        db.add_all(days)
        await db.commit()

