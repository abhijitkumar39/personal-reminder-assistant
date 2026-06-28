from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import settings


class Base(DeclarativeBase):
    pass


engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False},
)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


from collections.abc import Generator

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import settings


class Base(DeclarativeBase):
    pass


engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False},
)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


def _migrate_db() -> None:
    inspector = inspect(engine)
    if "reminders" not in inspector.get_table_names():
        return

    columns = {column["name"] for column in inspector.get_columns("reminders")}
    with engine.begin() as conn:
        if "recurrence" not in columns:
            conn.execute(
                text(
                    "ALTER TABLE reminders ADD COLUMN recurrence VARCHAR(20) "
                    "NOT NULL DEFAULT 'none'"
                )
            )
        if "recurrence_end_at" not in columns:
            conn.execute(
                text("ALTER TABLE reminders ADD COLUMN recurrence_end_at DATETIME")
            )


def init_db() -> None:
    import app.models.reminder  # noqa: F401

    Base.metadata.create_all(bind=engine)
    _migrate_db()


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
