"""Configuration and SDK-surface tests for the Composio client factory.

These tests never contact Composio. They prove that the installed SDK can
be constructed and exposes the account-action surfaces the planned module
will need.
"""

import os

import pytest

# Composio creates its file cache during import. Keep that cache in a
# writable temporary location in restricted/CI environments.
os.environ.setdefault("COMPOSIO_CACHE_DIR", "/tmp/vc-coldemailer-composio-test-cache")

from app.composio_client import get_composio  # noqa: E402


@pytest.fixture(autouse=True)
def _clear_client_cache():
    get_composio.cache_clear()
    yield
    get_composio.cache_clear()


def test_get_composio_requires_api_key(monkeypatch):
    monkeypatch.delenv("COMPOSIO_API_KEY", raising=False)

    with pytest.raises(RuntimeError, match="COMPOSIO_API_KEY"):
        get_composio()


def test_get_composio_constructs_cached_sdk_with_required_surfaces(monkeypatch):
    monkeypatch.setenv("COMPOSIO_API_KEY", "test-key")

    client = get_composio()

    assert client is get_composio()
    assert callable(client.tools.execute)
    assert callable(client.tools.get)
    assert callable(client.connected_accounts.list)
    assert hasattr(client, "triggers")
