from httpx import ASGITransport, AsyncClient

from app.composio_outreach import reset_state
from app.composio_routes import _composio_dependency
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


async def test_status_returns_503_not_500_when_composio_not_configured(monkeypatch):
    monkeypatch.delenv("COMPOSIO_API_KEY", raising=False)
    from app.composio_client import get_composio as real_get_composio

    real_get_composio.cache_clear()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/integrations/gmail/status")
    assert response.status_code == 503
    assert response.json()["detail"]["error"]["code"] == "integration_not_configured"


async def test_send_returns_503_not_500_when_composio_not_configured(monkeypatch):
    monkeypatch.delenv("COMPOSIO_API_KEY", raising=False)
    from app.composio_client import get_composio as real_get_composio

    real_get_composio.cache_clear()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/drafts/some-id/send", headers={"Idempotency-Key": "key-1"}
        )
    assert response.status_code == 503
    assert response.json()["detail"]["error"]["code"] == "integration_not_configured"


async def test_full_connect_draft_approve_send_flow(monkeypatch):
    monkeypatch.setenv("COMPOSIO_AUTH_CONFIG_GMAIL", "ac_123")
    monkeypatch.setenv("COMPOSIO_CALLBACK_URL", "https://app.example.com/cb")
    monkeypatch.setenv("OPENAI_MODEL_DRAFTER", "gpt-5.6-terra")

    app.dependency_overrides[_composio_dependency] = lambda: _FakeComposio()
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
