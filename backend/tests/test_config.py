from app.config import Settings
from app.db import _connect_args_for


def test_normalize_railway_postgres_url():
    settings = Settings(database_url="postgres://user:pass@host:5432/railway")
    assert settings.database_url == "postgresql://user:pass@host:5432/railway"


def test_sqlite_url_unchanged():
    settings = Settings(database_url="sqlite:///./data/rupee_radar.db")
    assert settings.database_url == "sqlite:///./data/rupee_radar.db"


def test_postgres_connect_args_require_ssl():
    args = _connect_args_for("postgresql://user:pass@host:5432/railway")
    assert args == {"sslmode": "require"}


def test_postgres_url_with_sslmode_unchanged():
    url = "postgresql://user:pass@host:5432/railway?sslmode=disable"
    assert _connect_args_for(url) == {}


def test_sqlite_connect_args_allow_threading():
    assert _connect_args_for("sqlite:///./data/rupee_radar.db") == {"check_same_thread": False}
