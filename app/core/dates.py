"""Days are keyed by a midnight-UTC epoch timestamp."""

import datetime as dt


def day_timestamp(day: dt.date) -> int:
    return int(dt.datetime.combine(day, dt.time.min, tzinfo=dt.UTC).timestamp())
