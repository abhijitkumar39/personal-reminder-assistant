from collections.abc import Generator

from app.core.config import Settings, settings


def get_settings() -> Generator[Settings, None, None]:
    yield settings
