from __future__ import annotations

from datetime import date, datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class OctenQuery(BaseModel):
    query: str
    include_domains: list[str] | None = None
    exclude_domains: list[str] | None = None
    published_after: date | None = None
    require_text: list[str] | None = None
    max_results: int = 10
    extract_content: bool = False
    content_token_limit: int | None = None

    def cache_key(self) -> str:
        return self.model_dump_json()


class OctenResult(BaseModel):
    url: str
    title: str | None = None
    snippet: str | None = None
    content: str | None = None
    published_at: datetime | None = None
    crawled_at: datetime | None = None
    raw: dict[str, Any] = Field(default_factory=dict)


class QueryOutcome(BaseModel):
    """One issued query and what came back — the unit the executor accounts for."""

    intent_id: UUID
    intent_kind: str
    query: OctenQuery
    results: list[OctenResult] = Field(default_factory=list)
    latency_ms: int = 0
    cache_hit: bool = False
    failed: bool = False
    failure_reason: str | None = None


class RetrievalStats(BaseModel):
    queries_planned: int = 0
    queries_issued: int = 0
    queries_deduped: int = 0
    cache_hits: int = 0
    failed_queries: int = 0
    results: int = 0
    wall_time_ms: int = 0
    p50_latency_ms: int = 0
    p95_latency_ms: int = 0
    max_concurrency: int = 0
    content_extractions: int = 0
    transport: str = "local_index"

    @property
    def failure_rate(self) -> float:
        return self.failed_queries / self.queries_issued if self.queries_issued else 0.0


class RetrievalBundle(BaseModel):
    outcomes: list[QueryOutcome] = Field(default_factory=list)
    stats: RetrievalStats = Field(default_factory=RetrievalStats)
