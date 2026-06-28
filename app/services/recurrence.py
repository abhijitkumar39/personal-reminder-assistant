from datetime import datetime, timedelta, timezone
from enum import Enum


class RecurrenceInterval(str, Enum):
    NONE = "none"
    HOURLY = "hourly"
    DAILY = "daily"
    WEEKLY = "weekly"


def compute_next_remind_at(
    recurrence: RecurrenceInterval,
    current: datetime,
) -> datetime:
    current = current if current.tzinfo else current.replace(tzinfo=timezone.utc)

    if recurrence == RecurrenceInterval.HOURLY:
        return current + timedelta(hours=1)
    if recurrence == RecurrenceInterval.DAILY:
        return current + timedelta(days=1)
    if recurrence == RecurrenceInterval.WEEKLY:
        return current + timedelta(weeks=1)

    raise ValueError(f"Cannot compute next occurrence for {recurrence}")
