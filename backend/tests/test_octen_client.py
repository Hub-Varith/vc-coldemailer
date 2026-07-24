"""Wire-format tests for the one module that knows Octen's shape."""

import httpx
import pytest

from app.config import Settings
from app.models import OctenQuery
from app.octen.client import LocalIndexClient, OctenClient, build_backend

from datetime import date


def _client(handler) -> OctenClient:
    transport = httpx.MockTransport(handler)
    settings = Settings(octen_api_key="test-key", simulate_latency=False)
    return OctenClient(settings, httpx.AsyncClient(base_url="https://api.octen.ai", transport=transport))


def test_to_wire_maps_our_names_to_octen_names():
    client = _client(lambda request: httpx.Response(200, json={"results": []}))
    body = client.to_wire(
        OctenQuery(
            query="bone conduction seed investor",
            published_after=date(2026, 1, 1),
            require_text=["Northstar"],
            include_domains=["techcrunch.com"],
            max_results=7,
            extract_content=True,
            content_token_limit=500,
        )
    )
    assert body["query"] == "bone conduction seed investor"
    assert body["num_results"] == 7
    assert body["start_published_date"] == "2026-01-01"
    assert body["include_text"] == ["Northstar"]
    assert body["include_domains"] == ["techcrunch.com"]
    assert body["contents"]["text"]["max_characters"] == 2000


def test_from_wire_keeps_raw_and_drops_urlless_rows(octen_payload):
    client = _client(lambda request: httpx.Response(200, json=octen_payload))
    results = client.from_wire(octen_payload)

    assert len(results) == 3, "the row without a url is not a result"
    assert results[0].url == "https://northstar.vc/notes/the-quiet-market"
    assert results[0].published_at is not None and results[0].published_at.year == 2026
    assert results[0].raw == octen_payload["results"][0], "raw payload survives a bad mapping"
    assert results[2].url.endswith("echospace-pre-seed"), "alternate key names (link/highlight) are mapped"


@pytest.mark.asyncio
async def test_search_returns_results_on_200(octen_payload):
    client = _client(lambda request: httpx.Response(200, json=octen_payload))
    results, failed = await client.search(OctenQuery(query="hearing"))
    assert failed is False
    assert len(results) == 3


@pytest.mark.asyncio
async def test_timeout_is_a_soft_failure_not_an_exception():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.TimeoutException("timed out", request=request)

    results, failed = await _client(handler).search(OctenQuery(query="hearing"))
    assert (results, failed) == ([], True), "a timeout is a dropped data point, never raised into the pipeline"


@pytest.mark.asyncio
async def test_retries_429_then_succeeds(octen_payload):
    attempts = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        attempts["n"] += 1
        if attempts["n"] == 1:
            return httpx.Response(429, headers={"Retry-After": "0"})
        return httpx.Response(200, json=octen_payload)

    results, failed = await _client(handler).search(OctenQuery(query="hearing"))
    assert attempts["n"] == 2
    assert failed is False and len(results) == 3


@pytest.mark.asyncio
async def test_gives_up_after_three_attempts_on_500():
    attempts = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        attempts["n"] += 1
        return httpx.Response(503)

    results, failed = await _client(handler).search(OctenQuery(query="hearing"))
    assert attempts["n"] == 3
    assert (results, failed) == ([], True)


def test_backend_selection_follows_config():
    assert isinstance(build_backend(Settings(octen_api_key=None)), LocalIndexClient)
    assert isinstance(build_backend(Settings(octen_api_key="k")), OctenClient)
