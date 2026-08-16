import asyncio
import logging

from app.core.config import settings
from app.services.ai import AiError, OllamaService
from app.services.telegram import TelegramError, TelegramService

logger = logging.getLogger(__name__)

FALLBACK_REPLY = "Sorry, I couldn't think right now. Please try again in a moment."
TYPING_REFRESH_SECONDS = 4


async def _keep_typing(telegram: TelegramService, chat_id: str | int) -> None:
    """Refresh Telegram's typing indicator until cancelled (action lasts ~5s)."""
    while True:
        try:
            await telegram.send_chat_action(chat_id, "typing")
        except TelegramError as exc:
            logger.warning("Failed to send typing action: %s", exc)
            return
        await asyncio.sleep(TYPING_REFRESH_SECONDS)


async def handle_update(
    telegram: TelegramService,
    ai: OllamaService,
    update: dict,
) -> None:
    message = update.get("message") or update.get("edited_message")
    if not isinstance(message, dict):
        return

    text = message.get("text")
    chat = message.get("chat") or {}
    chat_id = chat.get("id")
    if not text or chat_id is None:
        return

    typing_task = asyncio.create_task(_keep_typing(telegram, chat_id))
    try:
        try:
            reply = await ai.generate_reply(text)
        except AiError as exc:
            logger.error("AI reply failed: %s", exc)
            reply = FALLBACK_REPLY
    finally:
        typing_task.cancel()
        try:
            await typing_task
        except asyncio.CancelledError:
            pass

    await telegram.send_message_to(chat_id, reply)
    logger.info("Replied to chat %s", chat_id)


async def telegram_bot_loop() -> None:
    """Long-poll Telegram and reply using local Ollama.

    Reminder scheduling / API stay separate; this only listens for inbound chats.
    """
    if not settings.telegram_bot_token:
        logger.warning("Telegram bot token missing; inbound bot loop disabled")
        return

    telegram = TelegramService(settings)
    ai = OllamaService(settings)
    offset: int | None = None

    try:
        await telegram.delete_webhook()
        logger.info(
            "Telegram inbound bot loop started (Ollama model=%s)",
            settings.ollama_model,
        )
    except TelegramError as exc:
        logger.error("Failed to prepare Telegram bot loop: %s", exc)
        return

    while True:
        try:
            updates = await telegram.get_updates(offset=offset, timeout_seconds=25)
            for update in updates:
                update_id = update.get("update_id")
                if isinstance(update_id, int):
                    offset = update_id + 1
                try:
                    await handle_update(telegram, ai, update)
                except TelegramError as exc:
                    logger.error("Failed to handle Telegram update: %s", exc)
        except TelegramError as exc:
            logger.error("Telegram getUpdates failed: %s", exc)
            await asyncio.sleep(3)
        except Exception:
            logger.exception("Telegram bot loop tick failed")
            await asyncio.sleep(3)
