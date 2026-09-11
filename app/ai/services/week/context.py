import datetime as dt
from collections.abc import Sequence

from app.core.dates import day_timestamp
from app.models import Day, Insight

from .window import Week

#: A day's AI items, keyed by that day's timestamp.
ItemsByDay = dict[int, list[Insight]]


def _items_block(label: str, items: Sequence[Insight]) -> list[str]:
    if not items:
        return []
    return [label, *(f"- {item.description}: {item.content}" for item in items)]


def build_week_context(
    *,
    week: Week,
    days: Sequence[Day],
    insights: ItemsByDay,
    suggestions: ItemsByDay,
    max_sections: int,
) -> str:
    ordered = sorted(days, key=lambda day: day.timestamp)
    written = {day.timestamp for day in ordered}

    blocks = [
        f"Week (UTC): {week.start.isoformat()} (Monday) to {week.end.isoformat()} (Sunday)",
        f"Days written: {len(ordered)} of {len(week.dates)}",
        f"Sections to write: {max_sections} at most, and fewer is better",
    ]

    missing = [d.strftime("%A %d %b") for d in week.dates if day_timestamp(d) not in written]
    if missing:
        blocks.append(f"No entry on: {', '.join(missing)}")

    for day in ordered:
        date = dt.datetime.fromtimestamp(day.timestamp, tz=dt.UTC).date()
        lines = [f"\n## {date.strftime('%A %d %b %Y')}"]

        if day.city is not None:
            lines.append(f"Place: {day.city.name}")
        if day.tags:
            lines.append(f"Tags: {', '.join(tag.name for tag in day.tags)}")
        if day.starred:
            lines.append("The user starred this day.")

        lines.append(f"Description: {day.description or '—'}")
        lines.extend(["Entry:", day.content or "—"])
        lines.extend(_items_block("Insights generated that day:", insights.get(day.timestamp, [])))
        lines.extend(
            _items_block("Suggestions generated that day:", suggestions.get(day.timestamp, []))
        )
        blocks.append("\n".join(lines))

    return "\n".join(blocks).strip()
