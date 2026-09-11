"""Week bounds for a digest, as the inclusive timestamp range the tables use."""

import datetime as dt
from dataclasses import dataclass

from app.core.dates import day_timestamp

DAYS_IN_WEEK = 7


@dataclass(frozen=True)
class Week:
    start: dt.date  # Monday
    end: dt.date  # Sunday

    @property
    def start_ts(self) -> int:
        return day_timestamp(self.start)

    @property
    def end_ts(self) -> int:
        return day_timestamp(self.end)

    @property
    def dates(self) -> list[dt.date]:
        return [self.start + dt.timedelta(days=i) for i in range(DAYS_IN_WEEK)]


def week_of(day: dt.date) -> Week:
    start = day - dt.timedelta(days=day.weekday())
    return Week(start=start, end=start + dt.timedelta(days=DAYS_IN_WEEK - 1))


def last_finished_week(now: dt.date | None = None) -> Week:
    today = now or dt.datetime.now(dt.UTC).date()
    return week_of(today - dt.timedelta(days=DAYS_IN_WEEK))
