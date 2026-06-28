from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.reminder import Reminder, ReminderStatus
from app.schemas.reminder import ReminderCreate, ReminderUpdate
from app.services.recurrence import RecurrenceInterval, compute_next_remind_at


class ReminderNotFoundError(Exception):
    pass


class ReminderNotPendingError(Exception):
    pass


def create_reminder(db: Session, payload: ReminderCreate) -> Reminder:
    reminder = Reminder(
        title=payload.title,
        message=payload.message,
        remind_at=payload.remind_at,
        recurrence=payload.recurrence,
        recurrence_end_at=payload.recurrence_end_at,
        status=ReminderStatus.PENDING,
    )
    db.add(reminder)
    db.commit()
    db.refresh(reminder)
    return reminder


def list_reminders(
    db: Session,
    status: ReminderStatus | None = None,
) -> list[Reminder]:
    query = select(Reminder).order_by(Reminder.remind_at)
    if status is not None:
        query = query.where(Reminder.status == status)
    return list(db.scalars(query))


def get_reminder(db: Session, reminder_id: int) -> Reminder:
    reminder = db.get(Reminder, reminder_id)
    if reminder is None:
        raise ReminderNotFoundError
    return reminder


def update_reminder(
    db: Session,
    reminder_id: int,
    payload: ReminderUpdate,
) -> Reminder:
    reminder = get_reminder(db, reminder_id)
    if reminder.status != ReminderStatus.PENDING:
        raise ReminderNotPendingError

    updates = payload.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(reminder, field, value)

    db.commit()
    db.refresh(reminder)
    return reminder


def cancel_reminder(db: Session, reminder_id: int) -> Reminder:
    reminder = get_reminder(db, reminder_id)
    if reminder.status != ReminderStatus.PENDING:
        raise ReminderNotPendingError

    reminder.status = ReminderStatus.CANCELLED
    db.commit()
    db.refresh(reminder)
    return reminder


def get_due_reminders(db: Session) -> list[Reminder]:
    now = datetime.now(timezone.utc)
    query = (
        select(Reminder)
        .where(Reminder.status == ReminderStatus.PENDING)
        .where(Reminder.remind_at <= now)
        .order_by(Reminder.remind_at)
    )
    return list(db.scalars(query))


def mark_reminder_sent(db: Session, reminder: Reminder) -> None:
    now = datetime.now(timezone.utc)
    reminder.sent_at = now

    recurrence = RecurrenceInterval(reminder.recurrence)
    if recurrence == RecurrenceInterval.NONE:
        reminder.status = ReminderStatus.SENT
        db.commit()
        return

    next_remind_at = compute_next_remind_at(recurrence, reminder.remind_at)
    if reminder.recurrence_end_at is not None:
        end_at = reminder.recurrence_end_at
        if end_at.tzinfo is None:
            end_at = end_at.replace(tzinfo=timezone.utc)
        if next_remind_at > end_at:
            reminder.status = ReminderStatus.SENT
            db.commit()
            return

    reminder.remind_at = next_remind_at
    db.commit()
