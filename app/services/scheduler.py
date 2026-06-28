import asyncio
import logging

from app.core.config import settings
from app.db.session import SessionLocal
from app.services.recurrence import RecurrenceInterval
from app.services.reminder import get_due_reminders, mark_reminder_sent
from app.services.telegram import TelegramError, TelegramService

logger = logging.getLogger(__name__)

_RECURRENCE_LABELS = {
    RecurrenceInterval.HOURLY: "every hour",
    RecurrenceInterval.DAILY: "every day",
    RecurrenceInterval.WEEKLY: "every week",
}


def _format_reminder_message(
    title: str,
    message: str | None,
    recurrence: str,
) -> str:
    body = message or title
    recurrence_interval = RecurrenceInterval(recurrence)
    if recurrence_interval == RecurrenceInterval.NONE:
        return f"Reminder: {title}\n\n{body}"

    label = _RECURRENCE_LABELS[recurrence_interval]
    return f"Reminder ({label}): {title}\n\n{body}"


async def process_due_reminders() -> None:
    telegram = TelegramService(settings)
    db = SessionLocal()
    try:
        due_reminders = get_due_reminders(db)
        for reminder in due_reminders:
            text = _format_reminder_message(
                reminder.title,
                reminder.message,
                reminder.recurrence,
            )
            try:
                await telegram.send_message(text)
            except TelegramError as exc:
                logger.error(
                    "Failed to send reminder %s: %s",
                    reminder.id,
                    exc,
                )
                continue

            mark_reminder_sent(db, reminder)
            logger.info("Sent reminder %s", reminder.id)
    finally:
        db.close()


async def reminder_scheduler_loop() -> None:
    while True:
        try:
            await process_due_reminders()
        except Exception:
            logger.exception("Reminder scheduler tick failed")
        await asyncio.sleep(settings.scheduler_interval_seconds)
