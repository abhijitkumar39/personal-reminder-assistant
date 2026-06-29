from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.reminder import Reminder, ReminderStatus
from app.schemas.reminder import ReminderCreate, ReminderUpdate
from app.services.recurrence import RecurrenceInterval, compute_next_remind_at
from app.utils.datetime import to_utc, utc_now


class ReminderNotFoundError(Exception):
    pass


class ReminderNotPendingError(Exception):
    pass


def create_reminder(db: Session, payload: ReminderCreate) -> Reminder:
    reminder = Reminder(
        title=payload.title,
        message=payload.message,
        remind_at=to_utc(payload.remind_at),
        recurrence=payload.recurrence,
        recurrence_end_at=(
            to_utc(payload.recurrence_end_at)
            if payload.recurrence_end_at is not None
            else None
        ),
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
        if field in {"remind_at", "recurrence_end_at"} and value is not None:
            value = to_utc(value)
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
    now = utc_now()
    query = (
        select(Reminder)
        .where(Reminder.status == ReminderStatus.PENDING)
        .where(Reminder.remind_at <= now.replace(tzinfo=None))
        .order_by(Reminder.remind_at)
    )
    return list(db.scalars(query))


def mark_reminder_sent(db: Session, reminder: Reminder) -> None:
    now = utc_now()
    reminder.sent_at = now.replace(tzinfo=None)

    recurrence = RecurrenceInterval(reminder.recurrence)
    if recurrence == RecurrenceInterval.NONE:
        reminder.status = ReminderStatus.SENT
        db.commit()
        return

    current = to_utc(reminder.remind_at)
    next_remind_at = compute_next_remind_at(recurrence, current)
    if reminder.recurrence_end_at is not None:
        end_at = to_utc(reminder.recurrence_end_at)
        if next_remind_at > end_at:
            reminder.status = ReminderStatus.SENT
            db.commit()
            return

    reminder.remind_at = next_remind_at.replace(tzinfo=None)
    db.commit()
