"""Pydantic contracts shared across every pipeline stage.

Every module boundary in this service passes one of these models -- never a
raw dict. Kept in a single file (rather than one file per stage, as a
strictly-modular layout would do) because the models are small and reading
the whole data shape of the pipeline in one place is more useful than
splitting it five ways.
"""

from datetime import date, datetime
from typing import Literal
from uuid import UUID

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
    investor_firm: str
    investor_person: str | None = None
    role: str | None = None
    score: float
    evidence: list[EvidenceRecord]  # sorted, strongest first
    lead_evidence: EvidenceRecord  # never stale; the email's opening fact
    contact_email: str | None = None
    firm_domain: str | None = None
    list_underfilled: bool = False


class TargetList(BaseModel):
    run_id: UUID
    profile_id: UUID
    generated_at: datetime
    rows: list[TargetRow]
    retrieval_stats: RetrievalStats
    warnings: list[str] = []


# --- Run lifecycle (for the HTTP API / store) ---------------------------------


class RunStatus(BaseModel):
    run_id: UUID
    profile_id: UUID
    state: Literal["pending", "planning", "retrieving", "extracting", "verifying", "scoring", "done", "failed"]
    error: str | None = None
    retrieval_stats: RetrievalStats | None = None
