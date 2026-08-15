import asyncio
import logging

from app.core.config import settings
from app.services.telegram import TelegramError, TelegramService

logger = logging.getLogger(__name__)

DEFAULT_REPLY = "How may I help you?"


async def handle_update(telegram: TelegramService, update: dict) -> None:
    message = update.get("message") or update.get("edited_message")
    if not isinstance(message, dict):
        return

    text = message.get("text")
    chat = message.get("chat") or {}
    chat_id = chat.get("id")
    if not text or chat_id is None:
        return

    await telegram.send_message_to(chat_id, DEFAULT_REPLY)
    logger.info("Replied to chat %s", chat_id)


async def telegram_bot_loop() -> None:
    """Long-poll Telegram and reply with a hardcoded message.

    Reminder scheduling / API stay separate; this only listens for inbound chats.
    """
    if not settings.telegram_bot_token:
        logger.warning("Telegram bot token missing; inbound bot loop disabled")
        return

    telegram = TelegramService(settings)
    offset: int | None = None

    try:
        await telegram.delete_webhook()
        logger.info("Telegram inbound bot loop started")
    except TelegramError as exc:
        logger.error("Failed to prepare Telegram bot loop: %s", exc)
        return

    while True:
        try:
            updates = await telegram.get_updates(offset=offset, timeout_seconds=25)
            print({"ok": True, "result": updates})
            for update in updates:
                update_id = update.get("update_id")
                if isinstance(update_id, int):
                    offset = update_id + 1
                try:
                    await handle_update(telegram, update)
                except TelegramError as exc:
                    logger.error("Failed to handle Telegram update: %s", exc)
        except TelegramError as exc:
            logger.error("Telegram getUpdates failed: %s", exc)
            await asyncio.sleep(3)
        except Exception:
            logger.exception("Telegram bot loop tick failed")
            await asyncio.sleep(3)
