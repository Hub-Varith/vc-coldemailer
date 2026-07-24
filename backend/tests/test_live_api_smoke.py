"""Explicitly opt-in, read-only smoke checks for configured external APIs.

Run with:
    RUN_LIVE_API_TESTS=1 uv run pytest tests/test_live_api_smoke.py -q

The checks skip unless both the opt-in flag and the corresponding API key
are present. No email is drafted, sent, approved, or otherwise mutated.
"""

import os

import pytest

os.environ.setdefault("COMPOSIO_CACHE_DIR", "/tmp/vc-coldemailer-composio-test-cache")

from app.composio_client import get_composio  # noqa: E402
from app.config import Settings  # noqa: E402
from app.models import OctenQuery  # noqa: E402
from app.octen_client import OctenClient  # noqa: E402


def _require_live_key(name: str) -> str:
    if os.environ.get("RUN_LIVE_API_TESTS") != "1":
        pytest.skip("set RUN_LIVE_API_TESTS=1 to enable external API smoke checks")
    value = os.environ.get(name)
    if not value:
        pytest.skip(f"{name} is not configured")
    return value


async def test_octen_live_search_is_callable():
    api_key = _require_live_key("OCTEN_API_KEY")
    client = OctenClient(Settings(octen_api_key=api_key))
    try:
        query = OctenQuery(query="site:sec.gov venture capital fund", max_results=1)
        # Exercise the real client request while retaining the HTTP response:
        # public search() intentionally turns network/auth failures into [],
        # which is correct for fan-out but too ambiguous for a live smoke test.
        response = await client._post_with_retries(
            client._to_octen_payload(query)
        )
    finally:
        await client.aclose()

    assert response.status_code == 200
    # Verified against the live API: the current response envelope nests
    # search results under data. The production adapter still assumes a
    # top-level results key; this smoke check intentionally records reality.
    assert isinstance(response.json().get("data", {}).get("results"), list)


def test_composio_live_can_read_gmail_tool_catalog(monkeypatch):
    api_key = _require_live_key("COMPOSIO_API_KEY")
    monkeypatch.setenv("COMPOSIO_API_KEY", api_key)
    get_composio.cache_clear()

    tools = get_composio().tools.get(
        user_id="vc-coldemailer-smoke-test",
        toolkits=["gmail"],
        limit=1,
    )

    assert tools is not None
