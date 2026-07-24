"""Pydantic contracts shared across every pipeline stage.

Every module boundary in this service passes one of these models -- never a
raw dict. Kept in a single file (rather than one file per stage, as a
strictly-modular layout would do) because the models are small and reading
the whole data shape of the pipeline in one place is more useful than
splitting it five ways.
"""

from datetime import date, datetime
from typing import Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

# --- Stage 1: company profile -----------------------------------------------


class ProfileCreate(BaseModel):
    """POST /profiles request body -- same as CompanyProfile minus the
    server-generated id."""

    company_name: str
    one_liner: str
    sector: str
    product_description: str
    stage: str
    geography: str
    target_check_size_usd: int | None = None
    founder_context: list[str] = []


class CompanyProfile(BaseModel):
    """What the founder tells us about their company and round, once."""

    id: UUID
    company_name: str
    one_liner: str
    sector: str
    product_description: str
    stage: str  # e.g. "seed", "series-a"
    geography: str
    target_check_size_usd: int | None = None
    # Free-text founder-background signals (e.g. "Stanford", "Bay Area").
    # Tiebreaker only, per BACKEND_SPEC.md Sec 5.7 -- scorer.py must never
    # let this promote an investor onto the list, only reorder near-ties.
    founder_context: list[str] = []


class ProfileUpdate(BaseModel):
    """PATCH /api/v1/profiles/{id} request body -- every field optional,
    only the ones present get applied."""

    company_name: str | None = None
    one_liner: str | None = None
    sector: str | None = None
    product_description: str | None = None
    stage: str | None = None
    geography: str | None = None
    target_check_size_usd: int | None = None
    founder_context: list[str] | None = None


class ProfileValidation(BaseModel):
    """POST /api/v1/profiles/{id}/validate response -- a cheap pre-flight
    read on whether the profile is specific enough to fill a list, before
    spending a run on it (API_ENDPOINTS.md Sec 3)."""

    ok: bool
    warnings: list[str] = []
    suggestions: list[str] = []


# --- Stage 2: search plan ----------------------------------------------------


class SearchIntent(BaseModel):
    """One angle of attack on 'who should fund this company' (e.g. adjacent
    portfolio bets, or partners publishing on this thesis), expanded into a
    batch of concrete Octen queries."""

    kind: Literal[
        "adjacent_portfolio",
        "thesis_signal",
        "fund_activity",
        "geo_crossing",
        "portfolio_gap",
        "recent_exit",
    ]
    rationale: str
    queries: list[str] = Field(min_length=5, max_length=30)
    domain_hints: list[str] = []
    recency_days: int | None = None


class SearchPlan(BaseModel):
    profile_id: UUID
    intents: list[SearchIntent]

    @property
    def query_count(self) -> int:
        return sum(len(intent.queries) for intent in self.intents)


# --- Stage 3: retrieval (Octen) ----------------------------------------------


class OctenQuery(BaseModel):
    """A single request to Octen. Field names here are OUR names, not
    Octen's wire format -- octen_client.py owns that translation."""

    query: str
    include_domains: list[str] | None = None
    exclude_domains: list[str] | None = None
    published_after: date | None = None
    require_text: list[str] | None = None
    max_results: int = 10
    extract_content: bool = False
    content_token_limit: int | None = None


class OctenResult(BaseModel):
    url: str
    title: str | None = None
    snippet: str | None = None
    content: str | None = None
    published_at: datetime | None = None
    crawled_at: datetime | None = None
    raw: dict = Field(default_factory=dict)


class RetrievedResult(BaseModel):
    """An OctenResult tagged with the intent that produced it, so the
    extractor knows what it was looking for."""

    result: OctenResult
    intent_kind: str
    query: str


class RetrievalStats(BaseModel):
    query_count: int
    result_count: int
    failed_query_count: int
    wall_time_s: float
    cache_hit_count: int = 0
    p50_latency_ms: float | None = None  # median single-query latency


class RetrievalBundle(BaseModel):
    profile_id: UUID
    results: list[RetrievedResult]
    stats: RetrievalStats


# --- Stage 4: evidence --------------------------------------------------------


class EvidenceRecord(BaseModel):
    """One checkable, dated fact about an investor or firm. This is the
    core unit of the product: it both qualifies the investor for the list
    and supplies the personalization for the outreach email."""

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
    claim: str
    event_date: date | None = None
    source_url: str
    source_published_at: date | None = None
    confidence: float = Field(ge=0.0, le=1.0)

    # Filled in by the verifier (stage 5), absent right after extraction.
    verified_at: datetime | None = None
    stale: bool = False


class InvestorRecord(BaseModel):
    """All evidence gathered for one investor/firm, pre-scoring."""

    firm: str
    firm_normalized: str  # "Acme Ventures" -> "acme", for dedupe/matching
    person: str | None = None
    role: str | None = None
    evidence: list[EvidenceRecord]


# --- Stage 6: output (the Composio contract) ----------------------------------


class TargetRow(BaseModel):
    # target_id is assigned once, at scoring time, and carried across
    # reverify runs (matched by firm+person) so a frontend that already
    # rendered this row keeps a stable ID to reference (API_ENDPOINTS.md
    # Sec 5) -- it is not part of the original BACKEND_SPEC.md Sec 7
    # contract but additive/optional there, so it doesn't break Composio.
    target_id: UUID = Field(default_factory=uuid4)
    investor_firm: str
    investor_person: str | None = None
    role: str | None = None
    score: float
    evidence: list[EvidenceRecord]  # sorted, strongest first
    lead_evidence: EvidenceRecord  # never stale; the email's opening fact
    contact_email: str | None = None
    firm_domain: str | None = None
    list_underfilled: bool = False
    # Mutable, founder-facing tracking state (API_ENDPOINTS.md Sec 5) --
    # the scorer never sets these to anything but the defaults; only
    # PATCH /targets/{id} and POST /targets/{id}/dismiss change them.
    status: Literal["new", "drafted", "approved", "sent", "replied", "dismissed", "needs_review"] = "new"
    notes: str | None = None


class TargetUpdate(BaseModel):
    """PATCH /api/v1/targets/{id} request body."""

    status: Literal["new", "drafted", "approved", "sent", "replied", "dismissed", "needs_review"] | None = None
    notes: str | None = None
    contact_email: str | None = None


class TargetSummary(BaseModel):
    """The row shape used in the paginated list endpoint -- lead evidence
    only, not the full evidence array, to keep the list payload small
    (API_ENDPOINTS.md Sec 5). GET /targets/{id} returns the full TargetRow."""

    target_id: UUID
    investor_firm: str
    investor_person: str | None = None
    role: str | None = None
    score: float
    status: str
    contact_email: str | None = None
    firm_domain: str | None = None
    evidence_count: int
    has_stale_evidence: bool
    lead_evidence: EvidenceRecord

    @staticmethod
    def from_row(row: "TargetRow") -> "TargetSummary":
        return TargetSummary(
            target_id=row.target_id,
            investor_firm=row.investor_firm,
            investor_person=row.investor_person,
            role=row.role,
            score=row.score,
            status=row.status,
            contact_email=row.contact_email,
            firm_domain=row.firm_domain,
            evidence_count=len(row.evidence),
            has_stale_evidence=any(e.stale for e in row.evidence),
            lead_evidence=row.lead_evidence,
        )


class TargetsPage(BaseModel):
    rows: list[TargetSummary]
    next_cursor: str | None = None
    list_underfilled: bool = False
    total: int


class TargetList(BaseModel):
    run_id: UUID
    profile_id: UUID
    generated_at: datetime
    rows: list[TargetRow]
    retrieval_stats: RetrievalStats
    warnings: list[str] = []


# --- Run lifecycle (for the HTTP API / store) ---------------------------------

RunStage = Literal[
    "queued", "planning", "retrieving", "extracting", "verifying", "scoring", "complete", "failed", "cancelled"
]


class RunProgress(BaseModel):
    queries_total: int = 0
    queries_done: int = 0
    results: int = 0
    evidence: int = 0
    investors: int = 0


class RunRetrievalStats(BaseModel):
    """API-facing view of RetrievalStats -- same numbers, millisecond
    field names to match API_ENDPOINTS.md Sec 4's example payload."""

    wall_time_ms: int
    cache_hits: int
    failed_queries: int
    p50_latency_ms: int | None = None

    @staticmethod
    def from_internal(stats: "RetrievalStats", p50_latency_ms: int | None = None) -> "RunRetrievalStats":
        return RunRetrievalStats(
            wall_time_ms=round(stats.wall_time_s * 1000),
            cache_hits=stats.cache_hit_count,
            failed_queries=stats.failed_query_count,
            p50_latency_ms=p50_latency_ms,
        )


class RunStatus(BaseModel):
    run_id: UUID
    profile_id: UUID
    status: Literal["queued", "running", "complete", "failed", "cancelled"]
    stage: RunStage
    progress: RunProgress = Field(default_factory=RunProgress)
    retrieval_stats: RunRetrievalStats | None = None
    warnings: list[str] = []
    error: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None


# --- HTTP error envelope (API_ENDPOINTS.md conventions) -----------------------


class ApiErrorBody(BaseModel):
    code: str
    message: str
    details: dict = Field(default_factory=dict)


class ApiErrorEnvelope(BaseModel):
    error: ApiErrorBody
