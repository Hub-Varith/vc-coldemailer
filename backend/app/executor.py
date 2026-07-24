"""Stage 3: run a SearchPlan's queries against Octen, concurrently.

This is the fan-out that makes the concurrency story real: a plan with
200-400 queries goes out under one semaphore and comes back as a single
RetrievalBundle with per-run timing attached. Two-phase retrieval (content
extraction only for survivors) happens one level up, in extractor.py --
this module's only job is "run these queries, fast, and don't let one
failure sink the batch".
"""

import asyncio
import logging
import time
from datetime import date, timedelta

from app.config import Settings
from app.models import OctenQuery, RetrievalBundle, RetrievalStats, RetrievedResult, SearchPlan
from app.octen_client import OctenClient

logger = logging.getLogger(__name__)


class _TtlCache:
    """Bare-minimum in-memory TTL cache, keyed by query hash. Good enough
    for v1 (per BACKEND_SPEC.md Sec 2) -- swap for Redis if this needs to
    survive across processes."""

    def __init__(self, ttl_s: int) -> None:
        self._ttl_s = ttl_s
        self._entries: dict[int, tuple[float, list]] = {}

    def get(self, key: int) -> list | None:
        entry = self._entries.get(key)
        if entry is None:
            return None
        expires_at, value = entry
        if time.monotonic() > expires_at:
            del self._entries[key]
            return None
        return value

    def set(self, key: int, value: list) -> None:
        self._entries[key] = (time.monotonic() + self._ttl_s, value)


# --- public API ---


async def execute(plan: SearchPlan, settings: Settings, octen_client: OctenClient, cache: _TtlCache | None = None) -> RetrievalBundle:
    """Flatten every intent's queries, dedupe, and fire them all under a
    concurrency cap. Individual query failures are dropped, not raised --
    see OctenClient.search, which already turns failures into empty lists."""
    cache = cache or _TtlCache(settings.octen_cache_ttl_s)
    queries = _flatten_and_dedupe(plan)
    logger.info("executing plan for profile=%s: %d unique queries", plan.profile_id, len(queries))

    semaphore = asyncio.Semaphore(settings.octen_max_concurrency)
    started_at = time.monotonic()

    async def _run_one(intent_kind: str, query: OctenQuery) -> tuple[str, OctenQuery, list]:
        cache_key = hash(query.model_dump_json())
        cached = cache.get(cache_key)
        if cached is not None:
            return intent_kind, query, cached
        async with semaphore:
            results = await octen_client.search(query)
        cache.set(cache_key, results)
        return intent_kind, query, results

    outcomes = await asyncio.gather(
        *(_run_one(intent_kind, query) for intent_kind, query in queries), return_exceptions=True
    )
    wall_time_s = time.monotonic() - started_at

    retrieved: list[RetrievedResult] = []
    failed_query_count = 0
    for outcome in outcomes:
        if isinstance(outcome, BaseException):
            failed_query_count += 1
            logger.warning("query task raised unexpectedly: %r", outcome)
            continue
        intent_kind, query, results = outcome
        retrieved.extend(RetrievedResult(result=r, intent_kind=intent_kind, query=query.query) for r in results)

    stats = RetrievalStats(
        query_count=len(queries),
        result_count=len(retrieved),
        failed_query_count=failed_query_count,
        wall_time_s=wall_time_s,
    )
    logger.info(
        "fan-out done for profile=%s: %d queries -> %d results in %.2fs (%d failed)",
        plan.profile_id, stats.query_count, stats.result_count, stats.wall_time_s, stats.failed_query_count,
    )
    return RetrievalBundle(profile_id=plan.profile_id, results=retrieved, stats=stats)


# --- private internals ---


def _flatten_and_dedupe(plan: SearchPlan) -> list[tuple[str, OctenQuery]]:
    """Every intent's query strings -> OctenQuery objects, with
    published_after applied from the intent's recency_days. Identical query
    strings are deduped before firing -- re-running a plan during
    development should not double the request count."""
    seen: set[str] = set()
    queries: list[tuple[str, OctenQuery]] = []
    for intent in plan.intents:
        published_after = date.today() - timedelta(days=intent.recency_days) if intent.recency_days else None
        for query_text in intent.queries:
            if query_text in seen:
                continue
            seen.add(query_text)
            queries.append((
                intent.kind,
                OctenQuery(
                    query=query_text,
                    include_domains=intent.domain_hints or None,
                    published_after=published_after,
                ),
            ))
    return queries
