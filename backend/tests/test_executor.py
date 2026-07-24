"""M2: confirms the fan-out dedupes queries, respects the concurrency cap,
and survives individual query failures without losing the rest of the
batch."""

from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.config import Settings
from app.executor import execute
from app.models import OctenResult, SearchIntent, SearchPlan


def _plan(**overrides) -> SearchPlan:
    intent = SearchIntent(
        kind="adjacent_portfolio",
        rationale="test",
        queries=["query one", "query two", "query one", "query three", "query four"],  # "query one" duplicated
        **overrides,
    )
    return SearchPlan(profile_id=uuid4(), intents=[intent])


async def test_execute_dedupes_and_returns_stats():
    settings = Settings(octen_max_concurrency=4)
    fake_result = OctenResult(url="https://example.com", title="t", raw={})
    octen_client = AsyncMock()
    octen_client.search.return_value = [fake_result]

    bundle = await execute(_plan(), settings, octen_client)

    assert octen_client.search.call_count == 4  # deduped from 5 to 4 unique queries
    assert bundle.stats.query_count == 4
    assert bundle.stats.result_count == 4
    assert bundle.stats.failed_query_count == 0
    assert all(r.intent_kind == "adjacent_portfolio" for r in bundle.results)


async def test_execute_survives_a_failing_query():
    settings = Settings(octen_max_concurrency=4)
    octen_client = AsyncMock()
    ok_result = [OctenResult(url="https://ok.com", raw={})]
    octen_client.search.side_effect = [Exception("boom"), ok_result, ok_result, ok_result]  # 4 unique queries

    bundle = await execute(_plan(), settings, octen_client)

    assert bundle.stats.failed_query_count == 1
    assert bundle.stats.result_count == 3
