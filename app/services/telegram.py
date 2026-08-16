import httpx

from app.core.config import Settings


class TelegramError(Exception):
    def __init__(self, message: str, status_code: int = 502) -> None:
        super().__init__(message)
        self.status_code = status_code


class TelegramService:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def _require_token(self) -> str:
        token = self._settings.telegram_bot_token
        if not token:
            raise TelegramError("Telegram bot token is not configured", status_code=503)
        return token

    def _require_default_chat_id(self) -> str:
        chat_id = self._settings.telegram_chat_id
        if not chat_id:
            raise TelegramError("Telegram chat ID is not configured", status_code=503)
        return chat_id

    def _api_url(self, method: str) -> str:
        token = self._require_token()
        return f"https://api.telegram.org/bot{token}/{method}"

    async def _post(self, method: str, payload: dict, timeout: float = 10.0) -> dict:
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.post(self._api_url(method), json=payload)
        except httpx.RequestError as exc:
            raise TelegramError(
                f"Failed to reach Telegram: {exc}",
                status_code=502,
            ) from exc

        data = response.json()
        if not response.is_success or not data.get("ok"):
            description = data.get("description", "Unknown Telegram API error")
            raise TelegramError(description, status_code=502)
        return data

    async def _get(self, method: str, params: dict, timeout: float = 10.0) -> dict:
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.get(self._api_url(method), params=params)
        except httpx.RequestError as exc:
            raise TelegramError(
                f"Failed to reach Telegram: {exc}",
                status_code=502,
            ) from exc

        data = response.json()
        if not response.is_success or not data.get("ok"):
            description = data.get("description", "Unknown Telegram API error")
            raise TelegramError(description, status_code=502)
        return data

    async def send_message(self, text: str) -> int:
        """Send to the configured default chat (used by reminder notifications)."""
        return await self.send_message_to(self._require_default_chat_id(), text)

    async def send_message_to(self, chat_id: str | int, text: str) -> int:
        data = await self._post(
            "sendMessage",
            {"chat_id": chat_id, "text": text},
        )
        result = data.get("result", {})
        message_id = result.get("message_id")
        if message_id is None:
            raise TelegramError("Telegram did not return a message ID", status_code=502)
        return message_id

    async def send_chat_action(self, chat_id: str | int, action: str = "typing") -> None:
        """Show a chat status like 'typing…' (expires after ~5 seconds on Telegram)."""
        await self._post(
            "sendChatAction",
            {"chat_id": chat_id, "action": action},
        )

    async def delete_webhook(self) -> None:
        """Ensure long polling works (webhook and getUpdates cannot both be active)."""
        await self._post("deleteWebhook", {"drop_pending_updates": False})

    async def get_updates(
        self,
        offset: int | None = None,
        timeout_seconds: int = 25,
    ) -> list[dict]:
        params: dict[str, int] = {"timeout": timeout_seconds}
        if offset is not None:
            params["offset"] = offset

        # HTTP timeout must be longer than Telegram's long-poll timeout.
        data = await self._get(
            "getUpdates",
            params,
            timeout=float(timeout_seconds + 10),
        )
        result = data.get("result", [])
        return result if isinstance(result, list) else []
