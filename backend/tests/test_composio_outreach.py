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
