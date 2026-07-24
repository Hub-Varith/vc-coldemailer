from unittest.mock import AsyncMock

import pytest

from app.composio_outreach import approve_draft, connect_gmail, draft_email, gmail_status, mark_gmail_active, reset_state, send_draft


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
