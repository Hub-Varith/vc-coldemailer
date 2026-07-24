# Composio Integration — Foundation & Outreach Core Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the first working vertical slice of the Composio module — connect Gmail via OAuth, look up prior contact, generate a draft, and send it with enforced idempotency — matching `BRIEF.md`'s "Hours 0–2: end-to-end send-with-approval path" priority and the design in `docs/superpowers/specs/2026-07-23-composio-integration-design.md`.

**Architecture:** Async SQLAlchemy 2.x + SQLite persistence layer, a `composio/` package of pure service functions that take an injected Composio client (real or fake) and never call an LLM to decide whether to act, and thin FastAPI routers under `/api/v1` that wire the two together. Every Composio account action goes through `app/composio_client.py`'s existing `get_composio()` singleton; every test goes through a `FakeComposio` double, never the live API.

**Tech Stack:** FastAPI, SQLAlchemy 2.x async (`aiosqlite` driver), Pydantic v2, `httpx.AsyncClient`/`ASGITransport` for route tests, `pytest-asyncio`.

## Global Constraints

- No Composio tool is ever called by an LLM — only by our own code, with arguments we constructed (design doc §2).
- `Idempotency-Key` is enforced by a DB unique constraint *before* any call to `GMAIL_SEND_EMAIL` — a retried request must not double-send (design doc §4.4, `API_ENDPOINTS.md` idempotency rule).
- Every module boundary is a Pydantic model — no dicts crossing from `composio/` into routes or vice versa (`BACKEND_SPEC.md` §0).
- Tests never hit the live Composio or OpenAI API — use `FakeComposio` / a stub OpenAI response (`BACKEND_SPEC.md` §0, design doc §6).
- No Celery — asyncio only (`BACKEND_SPEC.md` §2). Follow-up sequencing and reply-detection webhooks are **out of scope for this plan** — they depend on the `Send` model built here and are covered by a follow-on plan.
- Single-tenant scope: a `FOUNDER_USER_ID` env var stands in for the founder's identity everywhere Composio needs a `user_id`. The multi-tenant auth system in `API_ENDPOINTS.md` §1 is not built yet and out of scope here.
- `sending_domain_verified` is stubbed as `SENDING_DOMAIN_VERIFIED` (env bool, default `true`) until the real domain-verification system exists.
- Composio auth-config IDs (`COMPOSIO_AUTH_CONFIG_GMAIL`) are created once via the Composio dashboard and passed in as env vars — never created programmatically per user.
- Disconnecting an integration **disables** the connected account (`connected_accounts.disable`) rather than deleting it — reversible, keeps history (design doc §7 open item, resolved here).

---

## Task 1: Async DB foundation

**Files:**
- Modify: `backend/pyproject.toml` (add `sqlalchemy`, `aiosqlite` deps; add `pytest-asyncio` dev dep; add `[tool.pytest.ini_options]`)
- Create: `backend/app/models_db/__init__.py`
- Create: `backend/app/models_db/base.py`
- Create: `backend/app/db.py`
- Test: `backend/tests/test_db.py`

**Interfaces:**
- Produces: `app.models_db.base.Base` (SQLAlchemy `DeclarativeBase`), `app.db.get_database_url() -> str`, `app.db.get_engine() -> AsyncEngine`, `app.db.get_sessionmaker() -> async_sessionmaker[AsyncSession]`, `app.db.get_session() -> AsyncIterator[AsyncSession]` (FastAPI dependency).

- [ ] **Step 1: Add dependencies**

```bash
cd backend
uv add sqlalchemy aiosqlite
uv add --dev pytest-asyncio
```

- [ ] **Step 2: Configure pytest-asyncio**

Add to `backend/pyproject.toml`:

```toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
```

- [ ] **Step 3: Write the failing test**

```python
# backend/tests/test_db.py
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
```

- [ ] **Step 4: Run test to verify it fails**

Run: `cd backend && uv run pytest tests/test_db.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.db'`

- [ ] **Step 5: Implement `Base`**

```python
# backend/app/models_db/__init__.py
```

```python
# backend/app/models_db/base.py
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass
```

- [ ] **Step 6: Implement `app/db.py`**

```python
# backend/app/db.py
import os
from collections.abc import AsyncIterator
from functools import lru_cache

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)


def get_database_url() -> str:
    return os.environ.get("DATABASE_URL", "sqlite+aiosqlite:///./dev.db")


@lru_cache
def get_engine() -> AsyncEngine:
    return create_async_engine(get_database_url())


def get_sessionmaker() -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(get_engine(), expire_on_commit=False)


async def get_session() -> AsyncIterator[AsyncSession]:
    async with get_sessionmaker()() as session:
        yield session
```

- [ ] **Step 7: Run test to verify it passes**

Run: `cd backend && uv run pytest tests/test_db.py -v`
Expected: PASS (4 tests)

- [ ] **Step 8: Wire table creation into app startup**

```python
# backend/app/main.py
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.db import get_engine
from app.models_db.base import Base


@asynccontextmanager
async def lifespan(app: FastAPI):
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield


app = FastAPI(title="VC Cold Emailer API", lifespan=lifespan)


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
```

- [ ] **Step 9: Commit**

```bash
git add backend/pyproject.toml backend/uv.lock backend/app/db.py backend/app/models_db backend/app/main.py backend/tests/test_db.py
git commit -m "feat: add async SQLAlchemy foundation"
```

---

## Task 2: ConnectedAccount model and repo

**Files:**
- Create: `backend/app/models_db/integration.py`
- Create: `backend/app/composio_store/__init__.py`
- Create: `backend/app/composio_store/connected_accounts.py`
- Test: `backend/tests/store/test_connected_accounts.py`
- Test: `backend/tests/conftest.py`

**Interfaces:**
- Consumes: `app.db.get_sessionmaker`, `app.models_db.base.Base` (Task 1)
- Produces: `app.models_db.integration.ConnectedAccount` (ORM model, fields: `id: str`, `user_id: str`, `provider: str`, `composio_connected_account_id: str | None`, `status: str`, `error_reason: str | None`, `connected_at: datetime | None`, `created_at: datetime`); `app.composio_store.connected_accounts.create_connected_account(session, *, user_id: str, provider: str, composio_connected_account_id: str) -> ConnectedAccount`; `get_connected_account(session, *, user_id: str, provider: str) -> ConnectedAccount | None`; `list_connected_accounts(session, *, user_id: str) -> list[ConnectedAccount]`; `update_status(session, *, account: ConnectedAccount, status: str, error_reason: str | None = None) -> ConnectedAccount`; a reusable `db_session` pytest fixture in `conftest.py`.

- [ ] **Step 1: Write the shared test DB fixture**

```python
# backend/tests/conftest.py
import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.models_db.base import Base


@pytest.fixture
async def db_session():
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        yield session

    await engine.dispose()
```

- [ ] **Step 2: Write the failing test**

```python
# backend/tests/store/__init__.py
```

```python
# backend/tests/store/test_connected_accounts.py
import pytest

from app.composio_store.connected_accounts import (
    create_connected_account,
    get_connected_account,
    list_connected_accounts,
    update_status,
)


async def test_create_and_get_connected_account(db_session):
    created = await create_connected_account(
        db_session,
        user_id="founder-1",
        provider="gmail",
        composio_connected_account_id="ca_abc123",
    )
    await db_session.commit()

    fetched = await get_connected_account(db_session, user_id="founder-1", provider="gmail")
    assert fetched is not None
    assert fetched.id == created.id
    assert fetched.status == "pending"
    assert fetched.composio_connected_account_id == "ca_abc123"


async def test_get_connected_account_returns_none_when_missing(db_session):
    assert await get_connected_account(db_session, user_id="founder-1", provider="notion") is None


async def test_list_connected_accounts_scopes_by_user(db_session):
    await create_connected_account(
        db_session, user_id="founder-1", provider="gmail", composio_connected_account_id="ca_1"
    )
    await create_connected_account(
        db_session, user_id="founder-2", provider="gmail", composio_connected_account_id="ca_2"
    )
    await db_session.commit()

    accounts = await list_connected_accounts(db_session, user_id="founder-1")
    assert [a.provider for a in accounts] == ["gmail"]


async def test_update_status_sets_status_and_error_reason(db_session):
    account = await create_connected_account(
        db_session, user_id="founder-1", provider="gmail", composio_connected_account_id="ca_1"
    )
    await db_session.commit()

    updated = await update_status(db_session, account=account, status="error", error_reason="oauth_denied")
    await db_session.commit()

    assert updated.status == "error"
    assert updated.error_reason == "oauth_denied"
```

- [ ] **Step 3: Run test to verify it fails**

Run: `cd backend && uv run pytest tests/store/test_connected_accounts.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.composio_store'`

- [ ] **Step 4: Implement the model**

```python
# backend/app/models_db/integration.py
import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models_db.base import Base


def _new_id() -> str:
    return str(uuid.uuid4())


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class ConnectedAccount(Base):
    __tablename__ = "connected_accounts"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_new_id)
    user_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    provider: Mapped[str] = mapped_column(String, nullable=False)
    composio_connected_account_id: Mapped[str | None] = mapped_column(String, nullable=True)
    status: Mapped[str] = mapped_column(String, nullable=False, default="pending")
    error_reason: Mapped[str | None] = mapped_column(String, nullable=True)
    connected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
```

- [ ] **Step 5: Implement the repo**

```python
# backend/app/composio_store/__init__.py
```

```python
# backend/app/composio_store/connected_accounts.py
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models_db.integration import ConnectedAccount


async def create_connected_account(
    session: AsyncSession, *, user_id: str, provider: str, composio_connected_account_id: str
) -> ConnectedAccount:
    account = ConnectedAccount(
        user_id=user_id,
        provider=provider,
        composio_connected_account_id=composio_connected_account_id,
        status="pending",
    )
    session.add(account)
    await session.flush()
    return account


async def get_connected_account(
    session: AsyncSession, *, user_id: str, provider: str
) -> ConnectedAccount | None:
    result = await session.execute(
        select(ConnectedAccount).where(
            ConnectedAccount.user_id == user_id, ConnectedAccount.provider == provider
        )
    )
    return result.scalar_one_or_none()


async def list_connected_accounts(session: AsyncSession, *, user_id: str) -> list[ConnectedAccount]:
    result = await session.execute(
        select(ConnectedAccount).where(ConnectedAccount.user_id == user_id)
    )
    return list(result.scalars().all())


async def update_status(
    session: AsyncSession, *, account: ConnectedAccount, status: str, error_reason: str | None = None
) -> ConnectedAccount:
    account.status = status
    account.error_reason = error_reason
    await session.flush()
    return account
```

- [ ] **Step 6: Run test to verify it passes**

Run: `cd backend && uv run pytest tests/store/test_connected_accounts.py -v`
Expected: PASS (4 tests)

- [ ] **Step 7: Commit**

```bash
git add backend/app/models_db/integration.py backend/app/composio_store backend/tests/conftest.py backend/tests/store
git commit -m "feat: add ConnectedAccount model and repo"
```

---

## Task 3: Composio connection lifecycle service

**Files:**
- Create: `backend/app/composio/__init__.py`
- Create: `backend/app/composio/integrations.py`
- Create: `backend/tests/composio/__init__.py`
- Create: `backend/tests/composio/fakes.py`
- Test: `backend/tests/composio/test_integrations.py`

**Interfaces:**
- Consumes: `app.composio_store.connected_accounts.{create_connected_account, get_connected_account, list_connected_accounts, update_status}` (Task 2), `app.models_db.integration.ConnectedAccount` (Task 2)
- Produces: `app.composio.integrations.connect_provider(session, composio_client, *, user_id, provider, auth_config_id, callback_url) -> ConnectResult` (Pydantic: `redirect_url: str`, `connection_id: str`); `refresh_status(session, composio_client, *, account) -> ConnectedAccount`; `disconnect_provider(session, composio_client, *, account) -> ConnectedAccount`; `tests.composio.fakes.FakeComposio` (a reusable test double every later task extends).

`FakeComposio` mirrors the real `composio.Composio` client's shape confirmed against current SDK docs: `connected_accounts.initiate(user_id, auth_config_id, callback_url)` returns an object with `.id` and `.redirect_url`; `connected_accounts.get(id)` returns an object with `.status`; `connected_accounts.disable(id)`. **Before wiring the real client, confirm `connected_accounts.initiate(...)`'s return type actually exposes `.id` for the pending connection** (design doc §7 flags this class of assumption) — the fake encodes today's best-known shape.

- [ ] **Step 1: Write the fake Composio client**

```python
# backend/tests/composio/fakes.py
from dataclasses import dataclass, field


@dataclass
class FakeConnectionRequest:
    id: str
    redirect_url: str


@dataclass
class FakeConnectedAccountStatus:
    id: str
    status: str


class FakeConnectedAccounts:
    def __init__(self):
        self.initiate_calls: list[dict] = []
        self.disable_calls: list[str] = []
        self._statuses: dict[str, str] = {}
        self._next_id = 0

    def initiate(self, *, user_id: str, auth_config_id: str, callback_url: str) -> FakeConnectionRequest:
        self.initiate_calls.append(
            {"user_id": user_id, "auth_config_id": auth_config_id, "callback_url": callback_url}
        )
        self._next_id += 1
        connection_id = f"ca_fake_{self._next_id}"
        self._statuses[connection_id] = "INITIATED"
        return FakeConnectionRequest(id=connection_id, redirect_url=f"https://composio.fake/oauth/{connection_id}")

    def get(self, connection_id: str) -> FakeConnectedAccountStatus:
        return FakeConnectedAccountStatus(id=connection_id, status=self._statuses.get(connection_id, "FAILED"))

    def disable(self, connection_id: str) -> None:
        self.disable_calls.append(connection_id)
        self._statuses[connection_id] = "INACTIVE"

    def set_status(self, connection_id: str, status: str) -> None:
        """Test helper: simulate the OAuth callback completing."""
        self._statuses[connection_id] = status


class FakeComposio:
    def __init__(self):
        self.connected_accounts = FakeConnectedAccounts()
```

- [ ] **Step 2: Write the failing test**

```python
# backend/tests/composio/test_integrations.py
from app.composio.integrations import connect_provider, disconnect_provider, refresh_status
from app.composio_store.connected_accounts import get_connected_account
from tests.composio.fakes import FakeComposio


async def test_connect_provider_creates_pending_account_and_returns_redirect(db_session):
    composio = FakeComposio()

    result = await connect_provider(
        db_session,
        composio,
        user_id="founder-1",
        provider="gmail",
        auth_config_id="ac_gmail_123",
        callback_url="https://app.example.com/callback",
    )
    await db_session.commit()

    assert result.redirect_url.startswith("https://composio.fake/oauth/")
    account = await get_connected_account(db_session, user_id="founder-1", provider="gmail")
    assert account.status == "pending"
    assert account.composio_connected_account_id == result.connection_id
    assert composio.connected_accounts.initiate_calls == [
        {
            "user_id": "founder-1",
            "auth_config_id": "ac_gmail_123",
            "callback_url": "https://app.example.com/callback",
        }
    ]


async def test_refresh_status_maps_active_to_connected(db_session):
    composio = FakeComposio()
    result = await connect_provider(
        db_session, composio, user_id="founder-1", provider="gmail",
        auth_config_id="ac_gmail_123", callback_url="https://app.example.com/callback",
    )
    await db_session.commit()
    composio.connected_accounts.set_status(result.connection_id, "ACTIVE")

    account = await get_connected_account(db_session, user_id="founder-1", provider="gmail")
    updated = await refresh_status(db_session, composio, account=account)
    await db_session.commit()

    assert updated.status == "connected"


async def test_refresh_status_maps_failed_to_error(db_session):
    composio = FakeComposio()
    result = await connect_provider(
        db_session, composio, user_id="founder-1", provider="gmail",
        auth_config_id="ac_gmail_123", callback_url="https://app.example.com/callback",
    )
    await db_session.commit()
    composio.connected_accounts.set_status(result.connection_id, "FAILED")

    account = await get_connected_account(db_session, user_id="founder-1", provider="gmail")
    updated = await refresh_status(db_session, composio, account=account)
    await db_session.commit()

    assert updated.status == "error"
    assert updated.error_reason == "composio_connection_failed"


async def test_disconnect_provider_disables_and_marks_disconnected(db_session):
    composio = FakeComposio()
    result = await connect_provider(
        db_session, composio, user_id="founder-1", provider="gmail",
        auth_config_id="ac_gmail_123", callback_url="https://app.example.com/callback",
    )
    await db_session.commit()

    account = await get_connected_account(db_session, user_id="founder-1", provider="gmail")
    updated = await disconnect_provider(db_session, composio, account=account)
    await db_session.commit()

    assert updated.status == "disconnected"
    assert composio.connected_accounts.disable_calls == [result.connection_id]
```

- [ ] **Step 3: Run test to verify it fails**

Run: `cd backend && uv run pytest tests/composio/test_integrations.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.composio'`

- [ ] **Step 4: Implement the service**

```python
# backend/app/composio/__init__.py
```

```python
# backend/app/composio/integrations.py
from typing import Protocol

from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.models_db.integration import ConnectedAccount
from app.composio_store.connected_accounts import create_connected_account, update_status

_STATUS_MAP = {
    "ACTIVE": "connected",
    "INITIATED": "pending",
    "FAILED": "error",
    "INACTIVE": "disconnected",
}


class ConnectResult(BaseModel):
    redirect_url: str
    connection_id: str


class ConnectedAccountsClient(Protocol):
    def initiate(self, *, user_id: str, auth_config_id: str, callback_url: str): ...
    def get(self, connection_id: str): ...
    def disable(self, connection_id: str) -> None: ...


class ComposioClient(Protocol):
    connected_accounts: ConnectedAccountsClient


async def connect_provider(
    session: AsyncSession,
    composio_client: ComposioClient,
    *,
    user_id: str,
    provider: str,
    auth_config_id: str,
    callback_url: str,
) -> ConnectResult:
    connection_request = composio_client.connected_accounts.initiate(
        user_id=user_id, auth_config_id=auth_config_id, callback_url=callback_url
    )
    await create_connected_account(
        session,
        user_id=user_id,
        provider=provider,
        composio_connected_account_id=connection_request.id,
    )
    return ConnectResult(redirect_url=connection_request.redirect_url, connection_id=connection_request.id)


async def refresh_status(
    session: AsyncSession, composio_client: ComposioClient, *, account: ConnectedAccount
) -> ConnectedAccount:
    remote = composio_client.connected_accounts.get(account.composio_connected_account_id)
    mapped_status = _STATUS_MAP.get(remote.status, "error")
    error_reason = "composio_connection_failed" if mapped_status == "error" else None
    return await update_status(session, account=account, status=mapped_status, error_reason=error_reason)


async def disconnect_provider(
    session: AsyncSession, composio_client: ComposioClient, *, account: ConnectedAccount
) -> ConnectedAccount:
    composio_client.connected_accounts.disable(account.composio_connected_account_id)
    return await update_status(session, account=account, status="disconnected")
```

- [ ] **Step 5: Run test to verify it passes**

Run: `cd backend && uv run pytest tests/composio/test_integrations.py -v`
Expected: PASS (4 tests)

- [ ] **Step 6: Commit**

```bash
git add backend/app/composio backend/tests/composio
git commit -m "feat: add Composio connection lifecycle service"
```

---

## Task 4: Integrations FastAPI routes

**Files:**
- Create: `backend/app/routers/__init__.py`
- Create: `backend/app/routers/integrations.py`
- Modify: `backend/app/main.py`
- Modify: `backend/tests/conftest.py`
- Test: `backend/tests/routes/test_integrations.py`

**Interfaces:**
- Consumes: `app.composio.integrations.{connect_provider, refresh_status, disconnect_provider}` (Task 3), `app.db.get_session` (Task 1), `app.composio_client.get_composio` (existing), `app.composio_store.connected_accounts.{get_connected_account, list_connected_accounts}` (Task 2)
- Produces: `POST /api/v1/integrations/{provider}/connect`, `GET /api/v1/integrations/{provider}/status`, `GET /api/v1/integrations`, `DELETE /api/v1/integrations/{provider}`; an `app_client` pytest fixture in `conftest.py` other route test tasks reuse.

Provider → auth-config-id lookup and the placeholder founder identity live in a small settings helper added in this task.

- [ ] **Step 1: Add settings helpers**

```python
# backend/app/settings.py
import os


def _require(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"{name} is not set")
    return value


def get_founder_user_id() -> str:
    return _require("FOUNDER_USER_ID")


_AUTH_CONFIG_ENV = {
    "gmail": "COMPOSIO_AUTH_CONFIG_GMAIL",
    "google_sheets": "COMPOSIO_AUTH_CONFIG_GOOGLE_SHEETS",
    "notion": "COMPOSIO_AUTH_CONFIG_NOTION",
}


def get_auth_config_id(provider: str) -> str:
    env_name = _AUTH_CONFIG_ENV.get(provider)
    if env_name is None:
        raise ValueError(f"unknown provider: {provider}")
    return _require(env_name)


def get_callback_url() -> str:
    return _require("COMPOSIO_CALLBACK_URL")


def is_sending_domain_verified() -> bool:
    return os.environ.get("SENDING_DOMAIN_VERIFIED", "true").lower() == "true"
```

- [ ] **Step 2: Add the app test client fixture**

```python
# backend/tests/conftest.py  (append)
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.composio_client import get_composio
from app.db import get_session
from app.main import app
from tests.composio.fakes import FakeComposio


@pytest_asyncio.fixture
async def app_client(db_session, monkeypatch):
    monkeypatch.setenv("FOUNDER_USER_ID", "founder-1")
    monkeypatch.setenv("COMPOSIO_AUTH_CONFIG_GMAIL", "ac_gmail_123")
    monkeypatch.setenv("COMPOSIO_AUTH_CONFIG_GOOGLE_SHEETS", "ac_sheets_123")
    monkeypatch.setenv("COMPOSIO_AUTH_CONFIG_NOTION", "ac_notion_123")
    monkeypatch.setenv("COMPOSIO_CALLBACK_URL", "https://app.example.com/callback")

    fake_composio = FakeComposio()

    async def _get_session_override():
        yield db_session

    app.dependency_overrides[get_session] = _get_session_override
    app.dependency_overrides[get_composio] = lambda: fake_composio

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        client.fake_composio = fake_composio
        yield client

    app.dependency_overrides.clear()
```

(This task's move of `db_session` reuse assumes Task 2's fixture already lives in `conftest.py` — confirm no name collision before appending.)

- [ ] **Step 3: Write the failing test**

```python
# backend/tests/routes/__init__.py
```

```python
# backend/tests/routes/test_integrations.py
async def test_connect_returns_redirect_url_and_connection_id(app_client):
    response = await app_client.post("/api/v1/integrations/gmail/connect")
    assert response.status_code == 200
    body = response.json()
    assert body["redirect_url"].startswith("https://composio.fake/oauth/")
    assert body["connection_id"]


async def test_status_reflects_pending_then_connected(app_client):
    connect_response = await app_client.post("/api/v1/integrations/gmail/connect")
    connection_id = connect_response.json()["connection_id"]

    pending = await app_client.get("/api/v1/integrations/gmail/status")
    assert pending.json()["status"] == "pending"

    app_client.fake_composio.connected_accounts.set_status(connection_id, "ACTIVE")
    connected = await app_client.get("/api/v1/integrations/gmail/status")
    assert connected.json()["status"] == "connected"


async def test_list_integrations_includes_disconnected_providers(app_client):
    await app_client.post("/api/v1/integrations/gmail/connect")

    response = await app_client.get("/api/v1/integrations")
    body = {item["provider"]: item["status"] for item in response.json()["integrations"]}
    assert body["gmail"] == "pending"
    assert body["notion"] == "disconnected"


async def test_disconnect_sets_status_disconnected(app_client):
    await app_client.post("/api/v1/integrations/gmail/connect")

    response = await app_client.delete("/api/v1/integrations/gmail")
    assert response.status_code == 200

    status = await app_client.get("/api/v1/integrations/gmail/status")
    assert status.json()["status"] == "disconnected"


async def test_status_404_when_never_connected(app_client):
    response = await app_client.get("/api/v1/integrations/notion/status")
    assert response.status_code == 404
```

- [ ] **Step 4: Run test to verify it fails**

Run: `cd backend && uv run pytest tests/routes/test_integrations.py -v`
Expected: FAIL with 404s (router not mounted) or import errors

- [ ] **Step 5: Implement the router**

```python
# backend/app/routers/__init__.py
```

```python
# backend/app/routers/integrations.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.composio.integrations import connect_provider, disconnect_provider, refresh_status
from app.composio_client import get_composio
from app.db import get_session
from app.settings import get_auth_config_id, get_callback_url, get_founder_user_id
from app.composio_store.connected_accounts import get_connected_account, list_connected_accounts

router = APIRouter(prefix="/integrations", tags=["integrations"])

PROVIDERS = ["gmail", "google_sheets", "notion"]


async def _get_account_or_404(session: AsyncSession, provider: str):
    account = await get_connected_account(session, user_id=get_founder_user_id(), provider=provider)
    if account is None:
        raise HTTPException(status_code=404, detail={"error": {"code": "integration_not_found", "message": provider}})
    return account


@router.post("/{provider}/connect")
async def connect(
    provider: str,
    session: AsyncSession = Depends(get_session),
    composio_client=Depends(get_composio),
):
    result = await connect_provider(
        session,
        composio_client,
        user_id=get_founder_user_id(),
        provider=provider,
        auth_config_id=get_auth_config_id(provider),
        callback_url=get_callback_url(),
    )
    await session.commit()
    return result


@router.get("/{provider}/status")
async def status(
    provider: str,
    session: AsyncSession = Depends(get_session),
    composio_client=Depends(get_composio),
):
    account = await _get_account_or_404(session, provider)
    updated = await refresh_status(session, composio_client, account=account)
    await session.commit()
    return {"provider": provider, "status": updated.status, "error_reason": updated.error_reason}


@router.get("")
async def list_integrations(session: AsyncSession = Depends(get_session)):
    accounts = {a.provider: a for a in await list_connected_accounts(session, user_id=get_founder_user_id())}
    return {
        "integrations": [
            {"provider": provider, "status": accounts[provider].status if provider in accounts else "disconnected"}
            for provider in PROVIDERS
        ]
    }


@router.delete("/{provider}")
async def disconnect(
    provider: str,
    session: AsyncSession = Depends(get_session),
    composio_client=Depends(get_composio),
):
    account = await _get_account_or_404(session, provider)
    await disconnect_provider(session, composio_client, account=account)
    await session.commit()
    return {"provider": provider, "status": "disconnected"}
```

- [ ] **Step 6: Mount the router**

```python
# backend/app/main.py  (add near the top-level app object)
from app.routers.integrations import router as integrations_router

app.include_router(integrations_router, prefix="/api/v1")
```

- [ ] **Step 7: Run test to verify it passes**

Run: `cd backend && uv run pytest tests/routes/test_integrations.py -v`
Expected: PASS (5 tests)

- [ ] **Step 8: Run the full suite**

Run: `cd backend && uv run pytest -v`
Expected: all tests PASS

- [ ] **Step 9: Commit**

```bash
git add backend/app/routers backend/app/main.py backend/app/settings.py backend/tests/conftest.py backend/tests/routes
git commit -m "feat: add /api/v1/integrations routes"
```

---

## Task 5: Draft model and repo

**Files:**
- Create: `backend/app/models_db/draft.py`
- Create: `backend/app/models/__init__.py`
- Create: `backend/app/models/composio_io.py`
- Create: `backend/app/composio_store/drafts.py`
- Test: `backend/tests/store/test_drafts.py`

**Interfaces:**
- Consumes: `app.models_db.base.Base` (Task 1)
- Produces: `app.models.composio_io.{LeadEvidence, PriorContactResult, DraftContent}` (Pydantic boundary models — see docstrings below for why these are standalone rather than importing Octen's not-yet-built `EvidenceRecord`); `app.models_db.draft.Draft` (ORM, fields: `id`, `target_id`, `contact_email`, `firm_domain`, `lead_evidence_claim`, `lead_evidence_source_url`, `lead_evidence_stale: bool`, `prior_contact_found: bool`, `prior_contact_summary: str | None`, `subject`, `body`, `word_count`, `blockers: str` (JSON-encoded list[str]), `version: int`, `status: str`, `created_at`); `app.composio_store.drafts.{create_draft, get_draft, add_draft_version}`.

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/store/test_drafts.py
from app.composio_store.drafts import add_draft_version, create_draft, get_draft


async def test_create_draft_persists_fields(db_session):
    draft = await create_draft(
        db_session,
        target_id="target-1",
        contact_email="partner@fund.vc",
        firm_domain="fund.vc",
        lead_evidence_claim="Backed Acme Health, announced March 2026",
        lead_evidence_source_url="https://example.com/news",
        lead_evidence_stale=False,
        prior_contact_found=False,
        prior_contact_summary=None,
        subject="Quick note on Acme Health",
        body="Hi ...",
        word_count=95,
        blockers=[],
    )
    await db_session.commit()

    fetched = await get_draft(db_session, draft_id=draft.id)
    assert fetched.target_id == "target-1"
    assert fetched.version == 1
    assert fetched.status == "drafted"
    assert fetched.blockers == []


async def test_create_draft_with_blockers_status_needs_review(db_session):
    draft = await create_draft(
        db_session,
        target_id="target-2",
        contact_email="partner@fund.vc",
        firm_domain="fund.vc",
        lead_evidence_claim="stale claim",
        lead_evidence_source_url="https://example.com/news",
        lead_evidence_stale=True,
        prior_contact_found=False,
        prior_contact_summary=None,
        subject="",
        body="",
        word_count=0,
        blockers=["stale_lead_evidence"],
    )
    await db_session.commit()

    assert draft.status == "needs_review"
    assert draft.blockers == ["stale_lead_evidence"]


async def test_add_draft_version_increments_version_and_updates_body(db_session):
    draft = await create_draft(
        db_session,
        target_id="target-1",
        contact_email="partner@fund.vc",
        firm_domain="fund.vc",
        lead_evidence_claim="claim",
        lead_evidence_source_url="https://example.com/news",
        lead_evidence_stale=False,
        prior_contact_found=False,
        prior_contact_summary=None,
        subject="v1 subject",
        body="v1 body",
        word_count=10,
        blockers=[],
    )
    await db_session.commit()

    updated = await add_draft_version(db_session, draft=draft, subject="v2 subject", body="v2 body", word_count=12)
    await db_session.commit()

    assert updated.version == 2
    assert updated.subject == "v2 subject"
    assert updated.body == "v2 body"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && uv run pytest tests/store/test_drafts.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.composio_store.drafts'`

- [ ] **Step 3: Implement the boundary models**

```python
# backend/app/models/__init__.py
```

```python
# backend/app/models/composio_io.py
"""Pydantic boundary types the composio/ package consumes.

These intentionally do NOT import Octen's EvidenceRecord/TargetRow — the
Octen module isn't built yet (BACKEND_SPEC.md M1-M6 hasn't started). This
is a minimal compatible subset; reconcile with the real TargetList/
EvidenceRecord contract at the M6 handoff (BACKEND_SPEC.md sec 11).
"""

from datetime import date

from pydantic import BaseModel


class LeadEvidence(BaseModel):
    claim: str
    source_url: str
    stale: bool = False
    event_date: date | None = None


class PriorContactResult(BaseModel):
    found: bool
    last_thread_at: str | None = None
    summary: str | None = None


class DraftContent(BaseModel):
    subject: str
    body: str
    word_count: int
```

- [ ] **Step 4: Implement the model**

```python
# backend/app/models_db/draft.py
import json
import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models_db.base import Base


def _new_id() -> str:
    return str(uuid.uuid4())


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Draft(Base):
    __tablename__ = "drafts"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_new_id)
    target_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    contact_email: Mapped[str] = mapped_column(String, nullable=False)
    firm_domain: Mapped[str] = mapped_column(String, nullable=False)
    lead_evidence_claim: Mapped[str] = mapped_column(Text, nullable=False)
    lead_evidence_source_url: Mapped[str] = mapped_column(String, nullable=False)
    lead_evidence_stale: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    prior_contact_found: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    prior_contact_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    subject: Mapped[str] = mapped_column(Text, nullable=False, default="")
    body: Mapped[str] = mapped_column(Text, nullable=False, default="")
    word_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    blockers_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    status: Mapped[str] = mapped_column(String, nullable=False, default="drafted")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    @property
    def blockers(self) -> list[str]:
        return json.loads(self.blockers_json)

    @blockers.setter
    def blockers(self, value: list[str]) -> None:
        self.blockers_json = json.dumps(value)
```

- [ ] **Step 5: Implement the repo**

```python
# backend/app/composio_store/drafts.py
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models_db.draft import Draft


async def create_draft(
    session: AsyncSession,
    *,
    target_id: str,
    contact_email: str,
    firm_domain: str,
    lead_evidence_claim: str,
    lead_evidence_source_url: str,
    lead_evidence_stale: bool,
    prior_contact_found: bool,
    prior_contact_summary: str | None,
    subject: str,
    body: str,
    word_count: int,
    blockers: list[str],
) -> Draft:
    draft = Draft(
        target_id=target_id,
        contact_email=contact_email,
        firm_domain=firm_domain,
        lead_evidence_claim=lead_evidence_claim,
        lead_evidence_source_url=lead_evidence_source_url,
        lead_evidence_stale=lead_evidence_stale,
        prior_contact_found=prior_contact_found,
        prior_contact_summary=prior_contact_summary,
        subject=subject,
        body=body,
        word_count=word_count,
        status="needs_review" if blockers else "drafted",
    )
    draft.blockers = blockers
    session.add(draft)
    await session.flush()
    return draft


async def get_draft(session: AsyncSession, *, draft_id: str) -> Draft | None:
    result = await session.execute(select(Draft).where(Draft.id == draft_id))
    return result.scalar_one_or_none()


async def add_draft_version(
    session: AsyncSession, *, draft: Draft, subject: str, body: str, word_count: int
) -> Draft:
    draft.subject = subject
    draft.body = body
    draft.word_count = word_count
    draft.version += 1
    await session.flush()
    return draft
```

- [ ] **Step 6: Run test to verify it passes**

Run: `cd backend && uv run pytest tests/store/test_drafts.py -v`
Expected: PASS (3 tests)

- [ ] **Step 7: Commit**

```bash
git add backend/app/models_db/draft.py backend/app/models backend/app/composio_store/drafts.py backend/tests/store/test_drafts.py
git commit -m "feat: add Draft model and repo"
```

---

## Task 6: Prior-contact lookup

**Files:**
- Create: `backend/app/composio/mail.py`
- Modify: `backend/tests/composio/fakes.py`
- Test: `backend/tests/composio/test_mail.py`

**Interfaces:**
- Consumes: `app.models.composio_io.PriorContactResult` (Task 5)
- Produces: `app.composio.mail.check_prior_contact(composio_client, *, user_id, connected_account_id, contact_email, firm_domain) -> PriorContactResult`; extends `FakeComposio` with a `tools` attribute other tasks (send) also extend.

- [ ] **Step 1: Extend the fake with `tools.execute`**

```python
# backend/tests/composio/fakes.py  (append)

class FakeTools:
    def __init__(self):
        self.execute_calls: list[dict] = []
        self.responses: dict[str, object] = {}

    def queue_response(self, tool_slug: str, response: object) -> None:
        self.responses[tool_slug] = response

    def execute(self, tool_slug: str, *, user_id: str, connected_account_id: str, arguments: dict) -> dict:
        self.execute_calls.append(
            {
                "tool_slug": tool_slug,
                "user_id": user_id,
                "connected_account_id": connected_account_id,
                "arguments": arguments,
            }
        )
        return self.responses.get(tool_slug, {"successful": True, "data": {}})
```

Update `FakeComposio.__init__` to also set `self.tools = FakeTools()`.

- [ ] **Step 2: Write the failing test**

```python
# backend/tests/composio/test_mail.py
from app.composio.mail import check_prior_contact
from tests.composio.fakes import FakeComposio


async def test_check_prior_contact_found():
    composio = FakeComposio()
    composio.tools.queue_response(
        "GMAIL_FETCH_EMAILS",
        {
            "successful": True,
            "data": {
                "messages": [
                    {"id": "m1", "internalDate": "1732000000000", "snippet": "Following up on our call"}
                ]
            },
        },
    )

    result = await check_prior_contact(
        composio,
        user_id="founder-1",
        connected_account_id="ca_gmail_1",
        contact_email="partner@fund.vc",
        firm_domain="fund.vc",
    )

    assert result.found is True
    assert result.summary == "Following up on our call"
    call = composio.tools.execute_calls[0]
    assert call["tool_slug"] == "GMAIL_FETCH_EMAILS"
    assert "partner@fund.vc" in call["arguments"]["query"]
    assert "fund.vc" in call["arguments"]["query"]


async def test_check_prior_contact_not_found():
    composio = FakeComposio()
    composio.tools.queue_response("GMAIL_FETCH_EMAILS", {"successful": True, "data": {"messages": []}})

    result = await check_prior_contact(
        composio,
        user_id="founder-1",
        connected_account_id="ca_gmail_1",
        contact_email="partner@fund.vc",
        firm_domain="fund.vc",
    )

    assert result.found is False
    assert result.summary is None
```

- [ ] **Step 3: Run test to verify it fails**

Run: `cd backend && uv run pytest tests/composio/test_mail.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.composio.mail'`

- [ ] **Step 4: Implement**

```python
# backend/app/composio/mail.py
from typing import Protocol

from app.models.composio_io import PriorContactResult


class ToolsExecutor(Protocol):
    def execute(self, tool_slug: str, *, user_id: str, connected_account_id: str, arguments: dict) -> dict: ...


class MailComposioClient(Protocol):
    tools: ToolsExecutor


async def check_prior_contact(
    composio_client: MailComposioClient,
    *,
    user_id: str,
    connected_account_id: str,
    contact_email: str,
    firm_domain: str,
) -> PriorContactResult:
    response = composio_client.tools.execute(
        "GMAIL_FETCH_EMAILS",
        user_id=user_id,
        connected_account_id=connected_account_id,
        arguments={"query": f"to:{contact_email} OR from:{contact_email} OR {firm_domain}", "max_results": 1},
    )
    messages = response.get("data", {}).get("messages", [])
    if not messages:
        return PriorContactResult(found=False)

    first = messages[0]
    return PriorContactResult(
        found=True,
        last_thread_at=first.get("internalDate"),
        summary=first.get("snippet"),
    )
```

- [ ] **Step 5: Run test to verify it passes**

Run: `cd backend && uv run pytest tests/composio/test_mail.py -v`
Expected: PASS (2 tests)

- [ ] **Step 6: Commit**

```bash
git add backend/app/composio/mail.py backend/tests/composio/fakes.py backend/tests/composio/test_mail.py
git commit -m "feat: add Composio prior-contact lookup"
```

**Verify before wiring the real client:** confirm `GMAIL_FETCH_EMAILS`'s actual response shape (`data.messages[].internalDate`/`.snippet` are assumed field names, mirroring `BACKEND_SPEC.md`'s "never invent Octen field names" rule extended to Composio) via `composio.tools.get(toolkits=["gmail"])` or a live call before removing this note.

---

## Task 7: Draft generation (OpenAI)

**Files:**
- Modify: `backend/app/openai_client.py`
- Modify: `backend/tests/test_openai_client.py`
- Create: `backend/app/composio/drafts.py`
- Create: `backend/app/routers/drafts.py`
- Modify: `backend/app/main.py`
- Test: `backend/tests/composio/test_drafts.py`
- Test: `backend/tests/routes/test_drafts.py`

**Interfaces:**
- Consumes: `app.models.composio_io.{LeadEvidence, PriorContactResult, DraftContent}` (Task 5), `app.composio_store.drafts.create_draft` (Task 5), `app.composio.mail.check_prior_contact` (Task 6), `app.composio_store.connected_accounts.get_connected_account` (Task 2)
- Produces: `app.openai_client.get_drafter_model() -> str`; `app.composio.drafts.generate_draft_content(openai_client, model, *, lead_evidence, prior_contact) -> DraftContent`; `POST /api/v1/targets/{target_id}/draft`, `GET /api/v1/drafts/{draft_id}`.

- [ ] **Step 1: Add the drafter model getter — failing test first**

```python
# backend/tests/test_openai_client.py  (append)
from app.openai_client import get_drafter_model


def test_get_drafter_model_returns_env_value(monkeypatch):
    monkeypatch.setenv("OPENAI_MODEL_DRAFTER", "gpt-5.6-terra")
    assert get_drafter_model() == "gpt-5.6-terra"


def test_get_drafter_model_raises_when_unset(monkeypatch):
    monkeypatch.delenv("OPENAI_MODEL_DRAFTER", raising=False)
    with pytest.raises(RuntimeError, match="OPENAI_MODEL_DRAFTER"):
        get_drafter_model()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && uv run pytest tests/test_openai_client.py -v`
Expected: FAIL with `ImportError: cannot import name 'get_drafter_model'`

- [ ] **Step 3: Implement**

```python
# backend/app/openai_client.py  (append)
def get_drafter_model() -> str:
    """Larger model for drafting outreach — one call per investor, on demand."""
    return _require("OPENAI_MODEL_DRAFTER")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && uv run pytest tests/test_openai_client.py -v`
Expected: PASS

- [ ] **Step 5: Write the failing draft-generation test**

```python
# backend/tests/composio/test_drafts.py
from unittest.mock import AsyncMock

from app.composio.drafts import generate_draft_content
from app.models.composio_io import DraftContent, LeadEvidence, PriorContactResult


async def test_generate_draft_content_parses_structured_response():
    fake_openai = AsyncMock()
    fake_openai.responses.parse.return_value.output_parsed = DraftContent(
        subject="Quick note on Acme Health",
        body="Hi Jordan — saw the Acme Health investment...",
        word_count=98,
    )

    lead_evidence = LeadEvidence(claim="Backed Acme Health, announced March 2026", source_url="https://x.com")
    prior_contact = PriorContactResult(found=False)

    result = await generate_draft_content(
        fake_openai, "gpt-5.6-terra", lead_evidence=lead_evidence, prior_contact=prior_contact
    )

    assert result.subject == "Quick note on Acme Health"
    assert 80 <= result.word_count <= 120 or result.word_count == 98
    fake_openai.responses.parse.assert_awaited_once()
```

- [ ] **Step 6: Run test to verify it fails**

Run: `cd backend && uv run pytest tests/composio/test_drafts.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.composio.drafts'`

- [ ] **Step 7: Implement draft generation**

```python
# backend/app/composio/drafts.py
from openai import AsyncOpenAI

from app.models.composio_io import DraftContent, LeadEvidence, PriorContactResult

_INSTRUCTIONS = (
    "Draft an 80-120 word cold outreach email to an investor. Open from the "
    "single lead evidence fact given — do not invent additional facts. If the "
    "founder has prior contact with this person, reference it naturally "
    "instead of writing as a cold intro."
)


async def generate_draft_content(
    openai_client: AsyncOpenAI,
    model: str,
    *,
    lead_evidence: LeadEvidence,
    prior_contact: PriorContactResult,
) -> DraftContent:
    prior_contact_note = (
        f"Prior contact found: {prior_contact.summary}" if prior_contact.found else "No prior contact."
    )
    response = await openai_client.responses.parse(
        model=model,
        instructions=_INSTRUCTIONS,
        input=f"Lead evidence: {lead_evidence.claim}\n{prior_contact_note}",
        text_format=DraftContent,
    )
    return response.output_parsed
```

- [ ] **Step 8: Run test to verify it passes**

Run: `cd backend && uv run pytest tests/composio/test_drafts.py -v`
Expected: PASS

- [ ] **Step 9: Write the failing route test**

```python
# backend/tests/routes/test_drafts.py
from unittest.mock import AsyncMock

from app.main import app
from app.models.composio_io import DraftContent
from app.openai_client import get_openai
from app.composio_store.connected_accounts import create_connected_account


async def test_draft_endpoint_creates_draft(app_client, db_session, monkeypatch):
    monkeypatch.setenv("OPENAI_MODEL_DRAFTER", "gpt-5.6-terra")
    await create_connected_account(
        db_session, user_id="founder-1", provider="gmail", composio_connected_account_id="ca_gmail_1"
    )
    await db_session.commit()
    app_client.fake_composio.connected_accounts.set_status("ca_gmail_1", "ACTIVE")
    app_client.fake_composio.tools.queue_response("GMAIL_FETCH_EMAILS", {"successful": True, "data": {"messages": []}})

    fake_openai = AsyncMock()
    fake_openai.responses.parse.return_value.output_parsed = DraftContent(
        subject="Quick note", body="Hi ...", word_count=90
    )
    app.dependency_overrides[get_openai] = lambda: fake_openai
    try:
        response = await _post_draft(app_client)
    finally:
        del app.dependency_overrides[get_openai]

    assert response.status_code == 200
    body = response.json()
    assert body["subject"] == "Quick note"
    assert body["blockers"] == []

    get_response = await app_client.get(f"/api/v1/drafts/{body['draft_id']}")
    assert get_response.json()["target_id"] == "target-1"


async def _post_draft(app_client):
    return await app_client.post(
        "/api/v1/targets/target-1/draft",
        json={
            "contact_email": "partner@fund.vc",
            "firm_domain": "fund.vc",
            "lead_evidence": {"claim": "Backed Acme Health, announced March 2026", "source_url": "https://x.com"},
        },
    )
```

- [ ] **Step 10: Run test to verify it fails**

Run: `cd backend && uv run pytest tests/routes/test_drafts.py -v`
Expected: FAIL with 404 (route not mounted)

- [ ] **Step 11: Implement the route**

```python
# backend/app/routers/drafts.py
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.composio.drafts import generate_draft_content
from app.composio.mail import check_prior_contact
from app.composio_client import get_composio
from app.db import get_session
from app.models.composio_io import LeadEvidence
from app.openai_client import get_drafter_model, get_openai
from app.settings import get_founder_user_id
from app.composio_store.connected_accounts import get_connected_account
from app.composio_store.drafts import create_draft, get_draft

router = APIRouter(tags=["drafts"])


class DraftRequest(BaseModel):
    contact_email: str
    firm_domain: str
    lead_evidence: LeadEvidence


@router.post("/targets/{target_id}/draft")
async def create_target_draft(
    target_id: str,
    body: DraftRequest,
    session: AsyncSession = Depends(get_session),
    composio_client=Depends(get_composio),
    openai_client=Depends(get_openai),
):
    account = await get_connected_account(session, user_id=get_founder_user_id(), provider="gmail")
    if account is None or account.status != "connected":
        raise HTTPException(status_code=409, detail={"error": {"code": "integration_not_connected", "message": "gmail"}})

    prior_contact = await check_prior_contact(
        composio_client,
        user_id=get_founder_user_id(),
        connected_account_id=account.composio_connected_account_id,
        contact_email=body.contact_email,
        firm_domain=body.firm_domain,
    )

    blockers = []
    if body.lead_evidence.stale:
        blockers.append("stale_lead_evidence")
    if prior_contact.found:
        blockers.append("prior_contact_exists")

    if body.lead_evidence.stale:
        content_subject, content_body, content_words = "", "", 0
    else:
        content = await generate_draft_content(
            openai_client, get_drafter_model(), lead_evidence=body.lead_evidence, prior_contact=prior_contact
        )
        content_subject, content_body, content_words = content.subject, content.body, content.word_count

    draft = await create_draft(
        session,
        target_id=target_id,
        contact_email=body.contact_email,
        firm_domain=body.firm_domain,
        lead_evidence_claim=body.lead_evidence.claim,
        lead_evidence_source_url=body.lead_evidence.source_url,
        lead_evidence_stale=body.lead_evidence.stale,
        prior_contact_found=prior_contact.found,
        prior_contact_summary=prior_contact.summary,
        subject=content_subject,
        body=content_body,
        word_count=content_words,
        blockers=blockers,
    )
    await session.commit()
    return {
        "draft_id": draft.id,
        "subject": draft.subject,
        "body": draft.body,
        "word_count": draft.word_count,
        "blockers": draft.blockers,
        "version": draft.version,
    }


@router.get("/drafts/{draft_id}")
async def get_draft_route(draft_id: str, session: AsyncSession = Depends(get_session)):
    draft = await get_draft(session, draft_id=draft_id)
    if draft is None:
        raise HTTPException(status_code=404, detail={"error": {"code": "draft_not_found", "message": draft_id}})
    return {
        "draft_id": draft.id,
        "target_id": draft.target_id,
        "subject": draft.subject,
        "body": draft.body,
        "word_count": draft.word_count,
        "blockers": draft.blockers,
        "version": draft.version,
        "status": draft.status,
    }
```

- [ ] **Step 12: Mount the router**

```python
# backend/app/main.py  (add alongside the integrations router)
from app.routers.drafts import router as drafts_router

app.include_router(drafts_router, prefix="/api/v1")
```

- [ ] **Step 13: Run test to verify it passes**

Run: `cd backend && uv run pytest tests/routes/test_drafts.py -v`
Expected: PASS

- [ ] **Step 14: Run the full suite**

Run: `cd backend && uv run pytest -v`
Expected: all tests PASS

- [ ] **Step 15: Commit**

```bash
git add backend/app/openai_client.py backend/app/composio/drafts.py backend/app/routers/drafts.py backend/app/main.py backend/tests/test_openai_client.py backend/tests/composio/test_drafts.py backend/tests/routes/test_drafts.py
git commit -m "feat: add draft generation service and routes"
```

---

## Task 8: Idempotent send

**Files:**
- Create: `backend/app/models_db/send.py`
- Create: `backend/app/composio_store/sends.py`
- Create: `backend/app/composio/send.py`
- Create: `backend/app/routers/sends.py`
- Modify: `backend/app/main.py`
- Modify: `backend/tests/composio/fakes.py`
- Test: `backend/tests/store/test_sends.py`
- Test: `backend/tests/composio/test_send.py`
- Test: `backend/tests/routes/test_sends.py`

**Interfaces:**
- Consumes: `app.composio_store.drafts.get_draft` (Task 5), `app.composio_store.connected_accounts.get_connected_account` (Task 2), `app.settings.is_sending_domain_verified` (Task 4)
- Produces: `app.models_db.send.Send` (ORM, fields: `id`, `draft_id`, `idempotency_key` (unique), `status`, `composio_message_id`, `error`, `created_at`); `app.composio_store.sends.{create_send, get_send_by_idempotency_key}`; `app.composio.send.send_gmail(composio_client, *, user_id, connected_account_id, to, subject, body) -> SendResult` (Pydantic: `message_id: str`); `POST /api/v1/drafts/{draft_id}/approve`, `POST /api/v1/drafts/{draft_id}/send`.

- [ ] **Step 1: Write the failing repo test**

```python
# backend/tests/store/test_sends.py
from app.composio_store.sends import create_send, get_send_by_idempotency_key


async def test_create_send_persists_and_is_fetchable_by_idempotency_key(db_session):
    send = await create_send(
        db_session, draft_id="draft-1", idempotency_key="key-1", status="sent", composio_message_id="msg-1"
    )
    await db_session.commit()

    fetched = await get_send_by_idempotency_key(db_session, idempotency_key="key-1")
    assert fetched.id == send.id
    assert fetched.composio_message_id == "msg-1"


async def test_get_send_by_idempotency_key_returns_none_when_missing(db_session):
    assert await get_send_by_idempotency_key(db_session, idempotency_key="nope") is None


async def test_idempotency_key_is_unique(db_session):
    await create_send(db_session, draft_id="draft-1", idempotency_key="dup", status="sent", composio_message_id="m1")
    await db_session.commit()

    with pytest.raises(Exception):
        await create_send(db_session, draft_id="draft-2", idempotency_key="dup", status="sent", composio_message_id="m2")
        await db_session.commit()
```

Add `import pytest` at the top of this file.

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && uv run pytest tests/store/test_sends.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.composio_store.sends'`

- [ ] **Step 3: Implement the model and repo**

```python
# backend/app/models_db/send.py
import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models_db.base import Base


def _new_id() -> str:
    return str(uuid.uuid4())


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Send(Base):
    __tablename__ = "sends"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_new_id)
    draft_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    idempotency_key: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    status: Mapped[str] = mapped_column(String, nullable=False)
    composio_message_id: Mapped[str | None] = mapped_column(String, nullable=True)
    error: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
```

```python
# backend/app/composio_store/sends.py
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models_db.send import Send


async def create_send(
    session: AsyncSession,
    *,
    draft_id: str,
    idempotency_key: str,
    status: str,
    composio_message_id: str | None = None,
    error: str | None = None,
) -> Send:
    send = Send(
        draft_id=draft_id,
        idempotency_key=idempotency_key,
        status=status,
        composio_message_id=composio_message_id,
        error=error,
    )
    session.add(send)
    await session.flush()
    return send


async def get_send_by_idempotency_key(session: AsyncSession, *, idempotency_key: str) -> Send | None:
    result = await session.execute(select(Send).where(Send.idempotency_key == idempotency_key))
    return result.scalar_one_or_none()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && uv run pytest tests/store/test_sends.py -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Extend the fake for `GMAIL_SEND_EMAIL`**

```python
# backend/tests/composio/fakes.py  (append to FakeTools, or use existing queue_response)
```

`FakeTools.execute` already returns queued responses generically — no change needed. In tests, call `composio.tools.queue_response("GMAIL_SEND_EMAIL", {"successful": True, "data": {"id": "msg-123"}})`.

- [ ] **Step 6: Write the failing send-service test**

```python
# backend/tests/composio/test_send.py
from app.composio.send import send_gmail
from tests.composio.fakes import FakeComposio


async def test_send_gmail_returns_message_id():
    composio = FakeComposio()
    composio.tools.queue_response("GMAIL_SEND_EMAIL", {"successful": True, "data": {"id": "msg-123"}})

    result = await send_gmail(
        composio,
        user_id="founder-1",
        connected_account_id="ca_gmail_1",
        to="partner@fund.vc",
        subject="Quick note",
        body="Hi ...",
    )

    assert result.message_id == "msg-123"
    call = composio.tools.execute_calls[0]
    assert call["tool_slug"] == "GMAIL_SEND_EMAIL"
    assert call["arguments"]["recipient_email"] == "partner@fund.vc"
```

- [ ] **Step 7: Run test to verify it fails**

Run: `cd backend && uv run pytest tests/composio/test_send.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.composio.send'`

- [ ] **Step 8: Implement**

```python
# backend/app/composio/send.py
from pydantic import BaseModel

from app.composio.mail import MailComposioClient


class SendResult(BaseModel):
    message_id: str


async def send_gmail(
    composio_client: MailComposioClient,
    *,
    user_id: str,
    connected_account_id: str,
    to: str,
    subject: str,
    body: str,
) -> SendResult:
    response = composio_client.tools.execute(
        "GMAIL_SEND_EMAIL",
        user_id=user_id,
        connected_account_id=connected_account_id,
        arguments={"recipient_email": to, "subject": subject, "body": body},
    )
    return SendResult(message_id=response["data"]["id"])
```

- [ ] **Step 9: Run test to verify it passes**

Run: `cd backend && uv run pytest tests/composio/test_send.py -v`
Expected: PASS

- [ ] **Step 10: Write the failing route test**

```python
# backend/tests/routes/test_sends.py
from app.composio_store.connected_accounts import create_connected_account
from app.composio_store.drafts import create_draft


async def _seed_draft_and_gmail(db_session):
    await create_connected_account(
        db_session, user_id="founder-1", provider="gmail", composio_connected_account_id="ca_gmail_1"
    )
    draft = await create_draft(
        db_session,
        target_id="target-1",
        contact_email="partner@fund.vc",
        firm_domain="fund.vc",
        lead_evidence_claim="claim",
        lead_evidence_source_url="https://x.com",
        lead_evidence_stale=False,
        prior_contact_found=False,
        prior_contact_summary=None,
        subject="Quick note",
        body="Hi ...",
        word_count=90,
        blockers=[],
    )
    await db_session.commit()
    return draft


async def test_send_requires_idempotency_key(app_client, db_session):
    draft = await _seed_draft_and_gmail(db_session)
    app_client.fake_composio.connected_accounts.set_status("ca_gmail_1", "ACTIVE")

    response = await app_client.post(f"/api/v1/drafts/{draft.id}/send")
    assert response.status_code == 400


async def test_send_succeeds_and_is_idempotent(app_client, db_session):
    draft = await _seed_draft_and_gmail(db_session)
    app_client.fake_composio.connected_accounts.set_status("ca_gmail_1", "ACTIVE")
    app_client.fake_composio.tools.queue_response("GMAIL_SEND_EMAIL", {"successful": True, "data": {"id": "msg-1"}})

    headers = {"Idempotency-Key": "key-abc"}
    first = await app_client.post(f"/api/v1/drafts/{draft.id}/send", headers=headers)
    assert first.status_code == 200
    assert first.json()["status"] == "sent"

    second = await app_client.post(f"/api/v1/drafts/{draft.id}/send", headers=headers)
    assert second.status_code == 200
    assert second.json() == first.json()

    assert len(
        [c for c in app_client.fake_composio.tools.execute_calls if c["tool_slug"] == "GMAIL_SEND_EMAIL"]
    ) == 1


async def test_send_rejected_when_domain_not_verified(app_client, db_session, monkeypatch):
    monkeypatch.setenv("SENDING_DOMAIN_VERIFIED", "false")
    draft = await _seed_draft_and_gmail(db_session)
    app_client.fake_composio.connected_accounts.set_status("ca_gmail_1", "ACTIVE")

    response = await app_client.post(
        f"/api/v1/drafts/{draft.id}/send", headers={"Idempotency-Key": "key-xyz"}
    )
    assert response.status_code == 409
```

- [ ] **Step 11: Run test to verify it fails**

Run: `cd backend && uv run pytest tests/routes/test_sends.py -v`
Expected: FAIL (route not mounted)

- [ ] **Step 12: Implement the route**

```python
# backend/app/routers/sends.py
from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.composio.send import send_gmail
from app.composio_client import get_composio
from app.db import get_session
from app.settings import get_founder_user_id, is_sending_domain_verified
from app.composio_store.connected_accounts import get_connected_account
from app.composio_store.drafts import get_draft
from app.composio_store.sends import create_send, get_send_by_idempotency_key

router = APIRouter(tags=["sends"])


@router.post("/drafts/{draft_id}/approve")
async def approve_draft(draft_id: str, session: AsyncSession = Depends(get_session)):
    draft = await get_draft(session, draft_id=draft_id)
    if draft is None:
        raise HTTPException(status_code=404, detail={"error": {"code": "draft_not_found", "message": draft_id}})
    if draft.blockers:
        raise HTTPException(status_code=409, detail={"error": {"code": "draft_has_blockers", "details": {"blockers": draft.blockers}}})
    draft.status = "approved"
    await session.commit()
    return {"draft_id": draft.id, "status": draft.status}


@router.post("/drafts/{draft_id}/send")
async def send_draft(
    draft_id: str,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    session: AsyncSession = Depends(get_session),
    composio_client=Depends(get_composio),
):
    if not idempotency_key:
        raise HTTPException(status_code=400, detail={"error": {"code": "idempotency_key_required", "message": ""}})

    existing = await get_send_by_idempotency_key(session, idempotency_key=idempotency_key)
    if existing is not None:
        return {"send_id": existing.id, "status": existing.status, "message_id": existing.composio_message_id}

    if not is_sending_domain_verified():
        raise HTTPException(status_code=409, detail={"error": {"code": "domain_unverified", "message": ""}})

    draft = await get_draft(session, draft_id=draft_id)
    if draft is None:
        raise HTTPException(status_code=404, detail={"error": {"code": "draft_not_found", "message": draft_id}})
    if draft.blockers:
        raise HTTPException(status_code=409, detail={"error": {"code": "draft_has_blockers", "details": {"blockers": draft.blockers}}})

    account = await get_connected_account(session, user_id=get_founder_user_id(), provider="gmail")
    if account is None or account.status != "connected":
        raise HTTPException(status_code=409, detail={"error": {"code": "integration_not_connected", "message": "gmail"}})

    result = await send_gmail(
        composio_client,
        user_id=get_founder_user_id(),
        connected_account_id=account.composio_connected_account_id,
        to=draft.contact_email,
        subject=draft.subject,
        body=draft.body,
    )

    send = await create_send(
        session, draft_id=draft.id, idempotency_key=idempotency_key, status="sent", composio_message_id=result.message_id
    )
    draft.status = "sent"
    await session.commit()
    return {"send_id": send.id, "status": send.status, "message_id": send.composio_message_id}
```

- [ ] **Step 13: Mount the router**

```python
# backend/app/main.py  (add alongside the other routers)
from app.routers.sends import router as sends_router

app.include_router(sends_router, prefix="/api/v1")
```

- [ ] **Step 14: Run test to verify it passes**

Run: `cd backend && uv run pytest tests/routes/test_sends.py -v`
Expected: PASS (3 tests)

- [ ] **Step 15: Run the full suite**

Run: `cd backend && uv run pytest -v`
Expected: all tests PASS

- [ ] **Step 16: Commit**

```bash
git add backend/app/models_db/send.py backend/app/composio_store/sends.py backend/app/composio/send.py backend/app/routers/sends.py backend/app/main.py backend/tests/store/test_sends.py backend/tests/composio/test_send.py backend/tests/composio/fakes.py backend/tests/routes/test_sends.py
git commit -m "feat: add idempotent Gmail send with approval gate"
```

---

## Deferred to follow-on plans

- **Sequencing & reply detection** (design doc §4.5–4.6): `SequenceStep` model, the DB-backed sweep task, `GMAIL_NEW_MESSAGE` trigger registration, and the `/webhooks/composio` handler. Depends on the `Send`/`Draft` models built here.
- **Export** (design doc §4.7): Sheets/Notion logging. Independent of sequencing; can be planned in parallel once tool slugs are confirmed (design doc §7).
- **Multi-tenant auth**: replacing `FOUNDER_USER_ID` with the real `User`/`/auth/*` system from `API_ENDPOINTS.md` §1.

## Parallelization notes for subagent-driven execution

Tasks 1→2→3→4 are strictly sequential (each builds the DB/service layer the next task's routes depend on). Once Task 4 lands, **Task 5 (Draft model) and Task 6 (prior-contact lookup) have no dependency on each other** and can run as two parallel subagents — both only depend on Task 2/3's `ConnectedAccount` plumbing and the shared `FakeComposio`. Task 7 depends on both 5 and 6. Task 8 depends on 5 and 4. Task 6 touches `tests/composio/fakes.py`, and Task 8 also touches it later — if 6 and 8 ever run concurrently, sequence 8 after 6 to avoid a merge conflict on that one file.
