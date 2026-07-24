# Composio Integration — Simple Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** The smallest working slice of the Composio module — connect Gmail, draft one email from a hardcoded evidence fact, send it with an idempotency check — matching `BRIEF.md`'s original "Hours 0-2" scope. This supersedes `2026-07-23-composio-integration-foundation.md` for execution: no database, no ORM, no Protocol abstractions. In-memory state only, same pattern Hub already used for `app/store.py` (`RunStore`) — explicitly sanctioned by `BACKEND_SPEC.md` §2 for v1/demo scope.

**Architecture:** One flat module, `app/composio_outreach.py`, holding three plain in-memory dicts (connection status, drafts, sent idempotency keys) and the functions that operate on them. One flat router file, `app/composio_routes.py`, with a handful of endpoints, included into the existing `app/main.py` via a single added line. No new files inside `app/models_db/`, `app/composio_store/`, or `app/routers/` from the prior plan — those are abandoned for now (already-committed Task 1/2 code from the old plan is left in place, just unused going forward).

**Tech Stack:** FastAPI, the existing `app.composio_client.get_composio()` and `app.openai_client.get_openai()` singletons. No SQLAlchemy, no `pytest-asyncio` beyond what Task 1 of the old plan already added (still available if needed).

## Global Constraints

- In-memory state, process-lifetime only — no persistence. This is explicit, sanctioned scope-narrowing (matches `app/store.py`'s own precedent), not an oversight.
- No LLM ever calls a Composio tool directly — OpenAI only generates draft text; our own code calls `composio.tools.execute(...)`.
- `Idempotency-Key` is required on send and checked against an in-memory `set()` before calling Composio — a retried request with the same key must not send twice.
- Do not touch `backend/app/main.py` beyond adding one `app.include_router(...)` line — that file is actively owned by a concurrent session (Hub); minimize footprint there to avoid another merge collision.
- Do not touch `app/store.py`, `app/models.py`, `app/config.py`, `app/pipeline.py`, `app/executor.py` — Hub's files.
- Providers in scope: `gmail` only (per user: no need to build Notion; Sheets/Notion logging is out of scope for this plan entirely, not just deferred).
- Tests use a fake Composio/OpenAI client, never the live API.

---

## Task 1: Connect Gmail + draft one email

**Files:**
- Create: `backend/app/composio_outreach.py`
- Test: `backend/tests/test_composio_outreach.py`

**Interfaces:**
- Produces: `connect_gmail(composio_client, *, user_id, auth_config_id, callback_url) -> dict` (returns `{"redirect_url": str, "connection_id": str}`, stores connection id + status "pending" in-memory); `gmail_status() -> str` (`"disconnected" | "pending" | "connected"`); `mark_gmail_active(composio_client)` (test/dev helper — calls `composio_client.connected_accounts.get(...)`, updates in-memory status); `draft_email(openai_client, model, *, contact_email, lead_evidence_claim) -> dict` (returns `{"draft_id": str, "subject": str, "body": str}`, stores in-memory).

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_composio_outreach.py
from unittest.mock import AsyncMock

from app.composio_outreach import connect_gmail, draft_email, gmail_status, reset_state


def setup_function():
    reset_state()


class FakeConnectedAccounts:
    def initiate(self, *, user_id, auth_config_id, callback_url):
        class R:
            id = "ca_fake_1"
            redirect_url = "https://composio.fake/oauth/ca_fake_1"
        return R()


class FakeComposio:
    def __init__(self):
        self.connected_accounts = FakeConnectedAccounts()


def test_connect_gmail_returns_redirect_and_sets_pending():
    result = connect_gmail(
        FakeComposio(), user_id="founder-1", auth_config_id="ac_123", callback_url="https://x.com/cb"
    )
    assert result["redirect_url"] == "https://composio.fake/oauth/ca_fake_1"
    assert gmail_status() == "pending"


async def test_draft_email_returns_subject_and_body():
    fake_openai = AsyncMock()
    fake_openai.responses.create.return_value.output_text = "Subject: Quick note\n\nHi Jordan, saw the Acme Health investment..."

    result = await draft_email(
        fake_openai, "gpt-5.6-terra", contact_email="partner@fund.vc", lead_evidence_claim="Backed Acme Health, announced March 2026"
    )
    assert result["draft_id"]
    assert "Acme" in fake_openai.responses.create.call_args.kwargs["input"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && uv run pytest tests/test_composio_outreach.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.composio_outreach'`

- [ ] **Step 3: Implement**

```python
# backend/app/composio_outreach.py
"""In-memory Composio outreach: connect Gmail, draft, send.

No database — matches app/store.py's own in-memory precedent
(BACKEND_SPEC.md Sec 2 explicitly allows this for v1/demo scope). State is
lost on restart; that's an accepted, deliberate simplification for this
pass, not an oversight.
"""

import uuid

_gmail_connection: dict = {"status": "disconnected", "connected_account_id": None}
_drafts: dict[str, dict] = {}
_sent_idempotency_keys: set[str] = set()


def reset_state() -> None:
    """Test-only: clear all in-memory state between tests."""
    _gmail_connection["status"] = "disconnected"
    _gmail_connection["connected_account_id"] = None
    _drafts.clear()
    _sent_idempotency_keys.clear()


def connect_gmail(composio_client, *, user_id: str, auth_config_id: str, callback_url: str) -> dict:
    connection_request = composio_client.connected_accounts.initiate(
        user_id=user_id, auth_config_id=auth_config_id, callback_url=callback_url
    )
    _gmail_connection["status"] = "pending"
    _gmail_connection["connected_account_id"] = connection_request.id
    return {"redirect_url": connection_request.redirect_url, "connection_id": connection_request.id}


def gmail_status() -> str:
    return _gmail_connection["status"]


def mark_gmail_active(composio_client) -> str:
    connection_id = _gmail_connection["connected_account_id"]
    remote = composio_client.connected_accounts.get(connection_id)
    _gmail_connection["status"] = "connected" if remote.status == "ACTIVE" else "error"
    return _gmail_connection["status"]


async def draft_email(openai_client, model: str, *, contact_email: str, lead_evidence_claim: str) -> dict:
    response = await openai_client.responses.create(
        model=model,
        instructions=(
            "Draft an 80-120 word cold outreach email to an investor. Open from "
            "the single evidence fact given — do not invent additional facts."
        ),
        input=f"Lead evidence: {lead_evidence_claim}\nContact: {contact_email}",
    )
    text = response.output_text
    subject, _, body = text.partition("\n\n")
    subject = subject.removeprefix("Subject:").strip()

    draft_id = str(uuid.uuid4())
    _drafts[draft_id] = {"contact_email": contact_email, "subject": subject, "body": body.strip(), "approved": False}
    return {"draft_id": draft_id, "subject": subject, "body": body.strip()}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && uv run pytest tests/test_composio_outreach.py -v`
Expected: PASS (2 tests)

- [ ] **Step 5: Commit**

```bash
git add backend/app/composio_outreach.py backend/tests/test_composio_outreach.py
git commit -m "feat: add in-memory Gmail connect and draft generation"
```

---

## Task 2: Approve and send with idempotency

**Files:**
- Modify: `backend/app/composio_outreach.py`
- Modify: `backend/tests/test_composio_outreach.py`

**Interfaces:**
- Consumes: `_drafts`, `_gmail_connection`, `_sent_idempotency_keys` (Task 1, same module)
- Produces: `approve_draft(draft_id: str) -> None` (raises `KeyError` if draft doesn't exist); `send_draft(composio_client, draft_id: str, idempotency_key: str) -> dict` (returns `{"status": "sent", "message_id": str}` or `{"status": "already_sent"}` on a repeated key; raises `ValueError` if not approved or Gmail not connected).

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_composio_outreach.py  (append)
import pytest

from app.composio_outreach import approve_draft, send_draft


class FakeTools:
    def execute(self, tool_slug, *, user_id, connected_account_id, arguments):
        return {"data": {"id": "msg-123"}}


class FakeComposioWithTools(FakeComposio):
    def __init__(self):
        super().__init__()
        self.tools = FakeTools()


async def _seed_approved_draft():
    fake_openai = AsyncMock()
    fake_openai.responses.create.return_value.output_text = "Subject: Hi\n\nBody text"
    draft = await draft_email(fake_openai, "gpt-5.6-terra", contact_email="p@fund.vc", lead_evidence_claim="claim")
    approve_draft(draft["draft_id"])
    return draft["draft_id"]


async def test_send_requires_gmail_connected():
    draft_id = await _seed_approved_draft()
    with pytest.raises(ValueError, match="gmail_not_connected"):
        await send_draft(FakeComposioWithTools(), draft_id, "key-1")


async def test_send_succeeds_and_is_idempotent():
    connect_gmail(FakeComposioWithTools(), user_id="founder-1", auth_config_id="ac_123", callback_url="https://x.com/cb")
    mark_gmail_active(_ActiveComposio())
    draft_id = await _seed_approved_draft()

    composio = FakeComposioWithTools()
    first = await send_draft(composio, draft_id, "key-1")
    assert first["status"] == "sent"

    second = await send_draft(composio, draft_id, "key-1")
    assert second["status"] == "already_sent"


class _ActiveConnectedAccounts:
    def get(self, connection_id):
        class R:
            status = "ACTIVE"
        return R()


class _ActiveComposio:
    def __init__(self):
        self.connected_accounts = _ActiveConnectedAccounts()
```

Add `from app.composio_outreach import connect_gmail, draft_email, gmail_status, mark_gmail_active, reset_state` already present at top; add `approve_draft, send_draft` to that import line.

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && uv run pytest tests/test_composio_outreach.py -v`
Expected: FAIL — `ImportError: cannot import name 'approve_draft'`

- [ ] **Step 3: Implement**

```python
# backend/app/composio_outreach.py  (append)

def approve_draft(draft_id: str) -> None:
    _drafts[draft_id]["approved"] = True


async def send_draft(composio_client, draft_id: str, idempotency_key: str) -> dict:
    if idempotency_key in _sent_idempotency_keys:
        return {"status": "already_sent"}

    if _gmail_connection["status"] != "connected":
        raise ValueError("gmail_not_connected")

    draft = _drafts[draft_id]
    if not draft["approved"]:
        raise ValueError("draft_not_approved")

    response = composio_client.tools.execute(
        "GMAIL_SEND_EMAIL",
        user_id="founder-1",
        connected_account_id=_gmail_connection["connected_account_id"],
        arguments={"recipient_email": draft["contact_email"], "subject": draft["subject"], "body": draft["body"]},
    )
    _sent_idempotency_keys.add(idempotency_key)
    return {"status": "sent", "message_id": response["data"]["id"]}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && uv run pytest tests/test_composio_outreach.py -v`
Expected: PASS (4 tests)

- [ ] **Step 5: Commit**

```bash
git add backend/app/composio_outreach.py backend/tests/test_composio_outreach.py
git commit -m "feat: add approve/send with idempotency"
```

**Note:** the idempotency check here is in-memory (`set()`), so it does NOT survive a process restart — a real deployment needs the DB-backed version from the old plan's Task 8. Acceptable for this pass; flag before shipping past a demo.

---

## Task 3: Wire up the routes

**Files:**
- Create: `backend/app/composio_routes.py`
- Modify: `backend/app/main.py` (one import + one `include_router` line only)
- Test: `backend/tests/test_composio_routes.py`

**Interfaces:**
- Consumes: everything from `app.composio_outreach` (Task 1, 2)
- Produces: `POST /api/v1/integrations/gmail/connect`, `GET /api/v1/integrations/gmail/status`, `POST /api/v1/targets/{target_id}/draft`, `POST /api/v1/drafts/{draft_id}/approve`, `POST /api/v1/drafts/{draft_id}/send`

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_composio_routes.py
from httpx import ASGITransport, AsyncClient

from app.composio_client import get_composio
from app.composio_outreach import reset_state
from app.main import app
from app.openai_client import get_openai


def setup_function():
    reset_state()


class _FakeComposio:
    class connected_accounts:
        @staticmethod
        def initiate(*, user_id, auth_config_id, callback_url):
            class R:
                id = "ca_1"
                redirect_url = "https://composio.fake/oauth/ca_1"
            return R()

        @staticmethod
        def get(connection_id):
            class R:
                status = "ACTIVE"
            return R()

    class tools:
        @staticmethod
        def execute(tool_slug, *, user_id, connected_account_id, arguments):
            return {"data": {"id": "msg-1"}}


class _FakeOpenAI:
    class responses:
        @staticmethod
        async def create(**kwargs):
            class R:
                output_text = "Subject: Quick note\n\nHi there"
            return R()


async def test_full_connect_draft_approve_send_flow(monkeypatch):
    monkeypatch.setenv("COMPOSIO_AUTH_CONFIG_GMAIL", "ac_123")
    monkeypatch.setenv("COMPOSIO_CALLBACK_URL", "https://app.example.com/cb")
    monkeypatch.setenv("OPENAI_MODEL_DRAFTER", "gpt-5.6-terra")

    app.dependency_overrides[get_composio] = lambda: _FakeComposio()
    app.dependency_overrides[get_openai] = lambda: _FakeOpenAI()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        connect = await client.post("/api/v1/integrations/gmail/connect")
        assert connect.status_code == 200

        status = await client.get("/api/v1/integrations/gmail/status")
        assert status.json()["status"] == "connected"

        draft = await client.post(
            "/api/v1/targets/target-1/draft",
            json={"contact_email": "partner@fund.vc", "lead_evidence_claim": "Backed Acme Health, announced March 2026"},
        )
        draft_id = draft.json()["draft_id"]

        approve = await client.post(f"/api/v1/drafts/{draft_id}/approve")
        assert approve.status_code == 200

        send = await client.post(f"/api/v1/drafts/{draft_id}/send", headers={"Idempotency-Key": "key-1"})
        assert send.json()["status"] == "sent"

    app.dependency_overrides.clear()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && uv run pytest tests/test_composio_routes.py -v`
Expected: FAIL — 404s, route not mounted

- [ ] **Step 3: Implement the router**

```python
# backend/app/composio_routes.py
"""Composio owner's routes. Adds exactly one line to app/main.py
(app.include_router(router)) — everything else lives here."""

import os

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel

from app.composio_client import get_composio
from app.composio_outreach import (
    approve_draft,
    draft_email,
    gmail_status,
    connect_gmail,
    mark_gmail_active,
    send_draft,
)
from app.openai_client import get_openai

router = APIRouter(prefix="/api/v1")


def _require(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"{name} is not set")
    return value


@router.post("/integrations/gmail/connect")
def connect(composio_client=Depends(get_composio)):
    return connect_gmail(
        composio_client,
        user_id="founder-1",
        auth_config_id=_require("COMPOSIO_AUTH_CONFIG_GMAIL"),
        callback_url=_require("COMPOSIO_CALLBACK_URL"),
    )


@router.get("/integrations/gmail/status")
def status(composio_client=Depends(get_composio)):
    if gmail_status() == "pending":
        mark_gmail_active(composio_client)
    return {"status": gmail_status()}


class DraftRequest(BaseModel):
    contact_email: str
    lead_evidence_claim: str


@router.post("/targets/{target_id}/draft")
async def create_draft(target_id: str, body: DraftRequest, openai_client=Depends(get_openai)):
    return await draft_email(
        openai_client,
        _require("OPENAI_MODEL_DRAFTER"),
        contact_email=body.contact_email,
        lead_evidence_claim=body.lead_evidence_claim,
    )


@router.post("/drafts/{draft_id}/approve")
def approve(draft_id: str):
    try:
        approve_draft(draft_id)
    except KeyError:
        raise HTTPException(status_code=404, detail={"error": {"code": "draft_not_found"}})
    return {"draft_id": draft_id, "status": "approved"}


@router.post("/drafts/{draft_id}/send")
async def send(draft_id: str, composio_client=Depends(get_composio), idempotency_key: str | None = Header(default=None, alias="Idempotency-Key")):
    if not idempotency_key:
        raise HTTPException(status_code=400, detail={"error": {"code": "idempotency_key_required"}})
    try:
        return await send_draft(composio_client, draft_id, idempotency_key)
    except ValueError as e:
        raise HTTPException(status_code=409, detail={"error": {"code": str(e)}})
```

- [ ] **Step 4: Mount the router — the only change to `main.py`**

```python
# backend/app/main.py  (add these two lines only; do not touch anything else in this file)
from app.composio_routes import router as composio_router

app.include_router(composio_router)
```

- [ ] **Step 5: Run test to verify it passes**

Run: `cd backend && uv run pytest tests/test_composio_routes.py -v`
Expected: PASS

- [ ] **Step 6: Run the full suite**

Run: `cd backend && uv run pytest -v`
Expected: all tests PASS

- [ ] **Step 7: Commit**

```bash
git add backend/app/composio_routes.py backend/app/main.py backend/tests/test_composio_routes.py
git commit -m "feat: wire Composio routes into the app"
```

---

## Deferred (not in this plan)

Everything from the old plan's Tasks 5-8 plus the design doc's sequencing/reply-detection/export sections: multiple targets, prior-contact lookup, follow-up sequences, reply webhooks, Sheets logging, persistence past a process restart. This plan is deliberately just enough to demo one hardcoded investor end-to-end.
