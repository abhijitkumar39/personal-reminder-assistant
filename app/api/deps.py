from collections.abc import Generator

from fastapi import Depends
from sqlalchemy.orm import Session

from app.core.config import Settings, settings
from app.db.session import get_db as get_db_session
from app.services.telegram import TelegramService


def get_settings() -> Generator[Settings, None, None]:
    yield settings


def get_db() -> Generator[Session, None, None]:
    yield from get_db_session()


def get_telegram_service(
    app_settings: Settings = Depends(get_settings),
) -> TelegramService:
    return TelegramService(app_settings)
