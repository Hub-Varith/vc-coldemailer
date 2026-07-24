import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from app.db import get_database_url, get_engine, get_sessionmaker
from app.models_db.base import Base


@pytest.fixture(autouse=True)
def _clear_cache():
    get_engine.cache_clear()
    yield
    get_engine.cache_clear()


def test_get_database_url_defaults_to_local_sqlite(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    assert get_database_url() == "sqlite+aiosqlite:///./dev.db"


def test_get_database_url_reads_env(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite+aiosqlite:///./custom.db")
    assert get_database_url() == "sqlite+aiosqlite:///./custom.db"


def test_get_engine_returns_async_engine_and_is_cached(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
    engine = get_engine()
    assert isinstance(engine, AsyncEngine)
    assert get_engine() is engine


async def test_base_metadata_creates_tables(monkeypatch, tmp_path):
    db_path = tmp_path / "test.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite+aiosqlite:///{db_path}")
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = get_sessionmaker()
    async with session_factory() as session:
        result = await session.execute(text("SELECT 1"))
        assert result.scalar_one() == 1

    await engine.dispose()
