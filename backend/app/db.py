from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import get_settings


class Base(DeclarativeBase):
    pass


def _connect_args_for(database_url: str) -> dict:
    if database_url.startswith("sqlite"):
        return {"check_same_thread": False}
    if database_url.startswith("postgresql") and "sslmode=" not in database_url:
        return {"sslmode": "require"}
    return {}


settings = get_settings()
connect_args = _connect_args_for(settings.database_url)
engine = create_engine(settings.database_url, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _migrate_sqlite_schema() -> None:
    """Add columns missing from older local DB files (create_all does not alter tables)."""
    if not settings.database_url.startswith("sqlite"):
        return

    from sqlalchemy import inspect, text

    inspector = inspect(engine)
    if not inspector.has_table("transactions"):
        return

    existing = {col["name"] for col in inspector.get_columns("transactions")}
    migrations = {
        "category_overridden": "ALTER TABLE transactions ADD COLUMN category_overridden BOOLEAN NOT NULL DEFAULT 0",
    }

    with engine.begin() as conn:
        for column, ddl in migrations.items():
            if column not in existing:
                conn.execute(text(ddl))


def init_db() -> None:
    import app.models  # noqa: F401

    Base.metadata.create_all(bind=engine)
    _migrate_sqlite_schema()
