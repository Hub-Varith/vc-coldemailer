"""The backend -> Composio handoff contract (BACKEND_SPEC.md §7).

FROZEN. This is the seam between the two owners. The Octen/pipeline owner
produces a `TargetList`; the Composio owner consumes it and owns everything
after. Do not change a field without telling the other owner first — a fixture
(`tests/fixtures/target_list.json`) is pinned to this shape so the Composio
side can build without running the pipeline.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel


class EvidenceRecord(BaseModel):
    investor_firm: str
    investor_person: str | None = None
    kind: Literal[
        "portfolio_investment",
        "thesis_publication",
        "fund_close",
        "portfolio_gap",
        "exit",
        "personnel",
        "other",
    ]
    claim: str  # one sentence, factual, no adjectives
    event_date: date | None = None
    source_url: str
    source_published_at: date | None = None
    confidence: float  # 0-1
    verified_at: datetime | None = None
    stale: bool = False


class RetrievalStats(BaseModel):
    query_count: int
    wall_time_s: float
    cache_hits: int = 0
    failed_queries: int = 0


class TargetRow(BaseModel):
    investor_firm: str
    investor_person: str | None = None
    role: str | None = None
    score: float
    evidence: list[EvidenceRecord]  # sorted, strongest first
    lead_evidence: EvidenceRecord  # never stale; the email's opening fact
    contact_email: str | None = None  # may be None — Composio resolves
    firm_domain: str | None = None
    list_underfilled: bool = False


class TargetList(BaseModel):
    run_id: UUID
    profile_id: UUID
    generated_at: datetime
    rows: list[TargetRow]
    retrieval_stats: RetrievalStats
    warnings: list[str] = []
