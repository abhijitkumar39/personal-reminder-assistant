from collections.abc import Generator

from fastapi import Depends

from app.core.config import Settings, settings
from app.services.telegram import TelegramService


def get_settings() -> Generator[Settings, None, None]:
    yield settings


def get_telegram_service(
    app_settings: Settings = Depends(get_settings),
) -> TelegramService:
    return TelegramService(app_settings)
