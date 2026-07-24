from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from .evidence import EvidenceRecord
from .retrieval import RetrievalStats

TargetStatus = Literal["new", "drafted", "approved", "sent", "replied", "dismissed", "needs_review"]


class TargetRow(BaseModel):
    """The handoff contract consumed by the Composio module (BACKEND_SPEC §7)."""

    target_id: UUID = Field(default_factory=uuid4)
    run_id: UUID
    investor_firm: str
    investor_person: str | None
    role: str | None = None
    score: float
    status: TargetStatus = "new"
    notes: str | None = None
    evidence: list[EvidenceRecord] = Field(default_factory=list)
    lead_evidence: EvidenceRecord
    contact_email: str | None = None
    firm_domain: str | None = None
    list_underfilled: bool = False
    # Display context carried through from the source record.
    location: str | None = None
    check_min: int | None = None
    check_max: int | None = None
    stage: list[str] = Field(default_factory=list)
    sectors: list[str] = Field(default_factory=list)
    score_breakdown: dict[str, float] = Field(default_factory=dict)
    draft_id: UUID | None = None

    @property
    def has_stale_evidence(self) -> bool:
        return any(e.stale for e in self.evidence)


class TargetSummary(BaseModel):
    """List-endpoint shape: lead evidence inline, full array withheld (API_ENDPOINTS §5)."""

    target_id: UUID
    run_id: UUID
    investor_firm: str
    investor_person: str | None
    role: str | None
    score: float
    status: TargetStatus
    contact_email: str | None
    firm_domain: str | None
    evidence_count: int
    has_stale_evidence: bool
    lead_evidence: EvidenceRecord
    location: str | None = None
    check_min: int | None = None
    check_max: int | None = None
    stage: list[str] = Field(default_factory=list)
    sectors: list[str] = Field(default_factory=list)
    draft_id: UUID | None = None


class TargetListPage(BaseModel):
    rows: list[TargetSummary]
    next_cursor: str | None = None
    list_underfilled: bool = False
    total: int = 0


class TargetList(BaseModel):
    run_id: UUID
    profile_id: UUID
    generated_at: datetime
    rows: list[TargetRow]
    retrieval_stats: RetrievalStats
    warnings: list[str] = Field(default_factory=list)


class TargetPatch(BaseModel):
    status: TargetStatus | None = None
    notes: str | None = None
    contact_email: str | None = None
