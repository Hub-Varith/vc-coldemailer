from __future__ import annotations

from datetime import date, datetime
from typing import Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

EvidenceKind = Literal[
    "portfolio_investment",
    "thesis_publication",
    "fund_close",
    "portfolio_gap",
    "exit",
    "personnel",
    "other",
]

#: Per-type staleness thresholds (BACKEND_SPEC §5.6). These decay at very different rates.
FRESHNESS_MAX_AGE_DAYS: dict[str, int] = {
    "personnel": 30,
    "fund_close": 180,
    "portfolio_investment": 90,
    "thesis_publication": 365,
    "portfolio_gap": 90,
    "exit": 365,
    "other": 120,
}

KIND_WEIGHT: dict[str, float] = {
    "thesis_publication": 1.0,
    "portfolio_investment": 0.95,
    "portfolio_gap": 0.8,
    "fund_close": 0.75,
    "exit": 0.7,
    "personnel": 0.4,
    "other": 0.3,
}


class EvidenceRecord(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    investor_firm: str
    investor_person: str | None = None
    kind: EvidenceKind
    claim: str
    detail: str = ""
    event_date: date | None = None
    source_url: str
    source_name: str = ""
    source_published_at: date | None = None
    confidence: float = 0.5
    verified_at: datetime | None = None
    stale: bool = False
    intent_kind: str = "other"

    @property
    def effective_date(self) -> date | None:
        return self.event_date or self.source_published_at

    def age_days(self, now: date) -> int | None:
        d = self.effective_date
        return (now - d).days if d else None


class InvestorRecord(BaseModel):
    """Evidence grouped under a person/firm, before scoring."""

    id: UUID = Field(default_factory=uuid4)
    investor_firm: str
    investor_person: str | None
    role: str | None = None
    firm_domain: str | None = None
    contact_email: str | None = None
    location: str | None = None
    check_min: int | None = None
    check_max: int | None = None
    stage: list[str] = Field(default_factory=list)
    sectors: list[str] = Field(default_factory=list)
    last_check_written: date | None = None
    affinities: list[str] = Field(default_factory=list)
    evidence: list[EvidenceRecord] = Field(default_factory=list)


class RejectedRecord(BaseModel):
    investor_firm: str
    investor_person: str | None
    reason: Literal["partner_departed", "fund_not_deploying", "evidence_stale", "no_evidence", "undated_evidence"]
    detail: str
    checked_at: datetime
