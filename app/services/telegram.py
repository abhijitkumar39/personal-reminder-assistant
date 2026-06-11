import httpx

from app.core.config import Settings


class TelegramError(Exception):
    def __init__(self, message: str, status_code: int = 502) -> None:
        super().__init__(message)
        self.status_code = status_code


class TelegramService:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def _validate_config(self) -> None:
        if not self._settings.telegram_bot_token:
            raise TelegramError("Telegram bot token is not configured", status_code=503)
        if not self._settings.telegram_chat_id:
            raise TelegramError("Telegram chat ID is not configured", status_code=503)

    async def send_message(self, text: str) -> int:
        self._validate_config()

        url = (
            f"https://api.telegram.org/bot{self._settings.telegram_bot_token}/sendMessage"
        )
        payload = {
            "chat_id": self._settings.telegram_chat_id,
            "text": text,
        }

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(url, json=payload)
        except httpx.RequestError as exc:
            raise TelegramError(
                f"Failed to reach Telegram: {exc}",
                status_code=502,
            ) from exc

        data = response.json()
        if not response.is_success or not data.get("ok"):
            description = data.get("description", "Unknown Telegram API error")
            raise TelegramError(description, status_code=502)

        result = data.get("result", {})
        message_id = result.get("message_id")
        if message_id is None:
            raise TelegramError("Telegram did not return a message ID", status_code=502)

        return message_id
