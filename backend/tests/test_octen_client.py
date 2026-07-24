"""M1: confirms the client maps Octen's wire format to our OctenResult
model correctly, and that retry/timeout handling never raises into the
caller."""

import json
from pathlib import Path

import httpx
import pytest
import respx

from app.config import Settings
from app.models import OctenQuery
from app.octen_client import OctenClient

FIXTURE = json.loads((Path(__file__).parent / "fixtures" / "octen_search_response.json").read_text())


def _client() -> OctenClient:
    settings = Settings(octen_api_key="test-key", octen_base_url="https://api.octen.ai")
    return OctenClient(settings)


@respx.mock
async def test_search_maps_results_and_keeps_raw_payload():
    respx.post("https://api.octen.ai/search").mock(return_value=httpx.Response(200, json=FIXTURE))

    client = _client()
    results = await client.search(OctenQuery(query="acme ventures seed hearing"))

    assert len(results) == 3
    first = results[0]
    assert first.url == FIXTURE["results"][0]["url"]
    assert first.title == FIXTURE["results"][0]["title"]
    assert first.published_at is not None
    assert first.raw == FIXTURE["results"][0]

    # missing dates must not raise -- they just come through as None
    assert results[2].published_at is None
    assert results[2].crawled_at is None

    await client.aclose()


@respx.mock
async def test_search_retries_on_429_then_succeeds():
    route = respx.post("https://api.octen.ai/search").mock(
        side_effect=[httpx.Response(429, headers={"Retry-After": "0"}), httpx.Response(200, json=FIXTURE)]
    )

    client = _client()
    results = await client.search(OctenQuery(query="retry me"))

    assert route.call_count == 2
    assert len(results) == 3
    await client.aclose()


@respx.mock
async def test_search_returns_empty_list_on_exhausted_retries_never_raises():
    respx.post("https://api.octen.ai/search").mock(return_value=httpx.Response(500))

    client = _client()
    results = await client.search(OctenQuery(query="always fails"))

    assert results == []
    await client.aclose()


@respx.mock
async def test_search_returns_empty_list_on_timeout():
    respx.post("https://api.octen.ai/search").mock(side_effect=httpx.TimeoutException("timed out"))

    client = _client()
    results = await client.search(OctenQuery(query="times out"))

    assert results == []
    await client.aclose()
