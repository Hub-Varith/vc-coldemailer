"""SearchPlan → RetrievalBundle: the fan-out (BACKEND_SPEC §5.4).

Several hundred narrow queries fired concurrently under a semaphore, deduped, cached, and
timed. Wall-clock time for the whole fan-out is surfaced in the API because it is the
selling point. A failed query is a dropped data point, never a failed run.
"""

from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import Awaitable, Callable
from datetime import date, timedelta

from ..config import Settings, get_settings
from ..models import (
    OctenQuery,
    QueryOutcome,
    RetrievalBundle,
    RetrievalStats,
    SearchPlan,
)
from .cache import TTLCache
from .client import SearchBackend, build_backend

log = logging.getLogger("proofline.octen.executor")

ProgressHook = Callable[[int, int, int], Awaitable[None]]
CONTENT_EXTRACTION_TOP_N = 50


def _percentile(values: list[int], pct: float) -> int:
    if not values:
        return 0
    ordered = sorted(values)
    index = min(len(ordered) - 1, int(round((len(ordered) - 1) * pct)))
    return ordered[index]


class Executor:
    def __init__(
        self,
        backend: SearchBackend | None = None,
        cache: TTLCache | None = None,
        settings: Settings | None = None,
    ) -> None:
        self._settings = settings or get_settings()
        self._backend = backend or build_backend(self._settings)
        self._cache = cache or TTLCache(self._settings.octen_cache_ttl_s)

    def build_queries(self, plan: SearchPlan, today: date | None = None) -> list[tuple[str, str, OctenQuery]]:
        today = today or date.today()
        seen: set[str] = set()
        queries: list[tuple[str, str, OctenQuery]] = []
        for intent in plan.intents:
            published_after = today - timedelta(days=intent.recency_days) if intent.recency_days else None
            for text in intent.queries:
                normalized = " ".join(text.lower().split())
                if normalized in seen:
                    continue
                seen.add(normalized)
                queries.append(
                    (
                        str(intent.id),
                        intent.kind,
                        OctenQuery(
                            query=text,
                            include_domains=intent.domain_hints or None,
                            published_after=published_after,
                            max_results=10,
                        ),
                    )
                )
        return queries

    async def execute(self, plan: SearchPlan, on_progress: ProgressHook | None = None) -> RetrievalBundle:
        planned = plan.query_count
        prepared = self.build_queries(plan)
        semaphore = asyncio.Semaphore(self._settings.octen_max_concurrency)
        started = time.perf_counter()
        done = 0
        in_flight = 0
        peak_concurrency = 0
        lock = asyncio.Lock()

        async def run_one(intent_id: str, intent_kind: str, query: OctenQuery) -> QueryOutcome:
            nonlocal done, in_flight, peak_concurrency
            cached = self._cache.get(query)
            if cached is not None:
                outcome = QueryOutcome(
                    intent_id=intent_id, intent_kind=intent_kind, query=query, results=cached, cache_hit=True
                )
            else:
                async with semaphore:
                    async with lock:
                        in_flight += 1
                        peak_concurrency = max(peak_concurrency, in_flight)
                    q_started = time.perf_counter()
                    results, failed = await self._backend.search(query)
                    latency_ms = int((time.perf_counter() - q_started) * 1000)
                    async with lock:
                        in_flight -= 1
                if not failed:
                    self._cache.put(query, results)
                outcome = QueryOutcome(
                    intent_id=intent_id,
                    intent_kind=intent_kind,
                    query=query,
                    results=results,
                    latency_ms=latency_ms,
                    failed=failed,
                    failure_reason="transport_or_timeout" if failed else None,
                )
            async with lock:
                done += 1
                current = done
            if on_progress and current % 25 == 0:
                await on_progress(current, len(prepared), sum(1 for _ in outcome.results))
            return outcome

        gathered = await asyncio.gather(
            *(run_one(intent_id, kind, query) for intent_id, kind, query in prepared), return_exceptions=True
        )
        outcomes: list[QueryOutcome] = []
        for item, (intent_id, kind, query) in zip(gathered, prepared):
            if isinstance(item, QueryOutcome):
                outcomes.append(item)
            else:
                log.warning("query task raised: %s", item)
                outcomes.append(
                    QueryOutcome(
                        intent_id=intent_id,
                        intent_kind=kind,
                        query=query,
                        failed=True,
                        failure_reason=type(item).__name__,
                    )
                )

        wall_ms = int((time.perf_counter() - started) * 1000)
        latencies = [o.latency_ms for o in outcomes if not o.cache_hit and not o.failed]
        stats = RetrievalStats(
            queries_planned=planned,
            queries_issued=len(prepared),
            queries_deduped=planned - len(prepared),
            cache_hits=sum(1 for o in outcomes if o.cache_hit),
            failed_queries=sum(1 for o in outcomes if o.failed),
            results=sum(len(o.results) for o in outcomes),
            wall_time_ms=wall_ms,
            p50_latency_ms=_percentile(latencies, 0.5),
            p95_latency_ms=_percentile(latencies, 0.95),
            max_concurrency=peak_concurrency,
            transport=self._backend.transport,
        )
        if on_progress:
            await on_progress(len(prepared), len(prepared), stats.results)
        log.info(
            "fan-out complete: %d queries in %dms (p50 %dms, peak concurrency %d, %d results, %d failures)",
            stats.queries_issued,
            stats.wall_time_ms,
            stats.p50_latency_ms,
            stats.max_concurrency,
            stats.results,
            stats.failed_queries,
        )
        return RetrievalBundle(outcomes=outcomes, stats=stats)

    async def extract_content(self, bundle: RetrievalBundle, urls: list[str]) -> RetrievalBundle:
        """Phase two: re-fetch only the top URLs with full-page extraction."""
        targets = urls[:CONTENT_EXTRACTION_TOP_N]
        if not targets:
            return bundle
        semaphore = asyncio.Semaphore(self._settings.octen_max_concurrency)

        async def fetch(url: str) -> tuple[str, str | None]:
            query = OctenQuery(query=url, max_results=1, extract_content=True, content_token_limit=1000)
            async with semaphore:
                results, failed = await self._backend.search(query)
            if failed or not results:
                return url, None
            return url, results[0].content

        fetched = dict(await asyncio.gather(*(fetch(url) for url in targets)))
        for outcome in bundle.outcomes:
            for result in outcome.results:
                content = fetched.get(result.url)
                if content:
                    result.content = content
        bundle.stats.content_extractions = sum(1 for v in fetched.values() if v)
        return bundle

    async def aclose(self) -> None:
        await self._backend.aclose()
