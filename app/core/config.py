from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent.parent
ENV_FILE = BASE_DIR / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(ENV_FILE),
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    app_name: str = "Personal Reminder Assistant"
    app_version: str = "0.2.0"
    debug: bool = False
    api_v1_prefix: str = "/api/v1"
    database_url: str = f"sqlite:///{BASE_DIR / 'reminders.db'}"
    scheduler_interval_seconds: int = 30
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""


settings = Settings()
