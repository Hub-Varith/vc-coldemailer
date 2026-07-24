"""Stage 5 (continued): score, rank, and cap the investor list.

Score is evidence strength x recency x kind weight, summed across an
investor's evidence so a fund with three good facts beats one with a
single weak one. Founder-context signals (shared school/region) are
applied strictly as a post-sort tiebreaker among near-equal scores -- they
can reorder who's #12 vs #13, never promote someone onto the list at all.
"""

import logging
from datetime import date

from app.config import Settings
from app.models import CompanyProfile, EvidenceRecord, InvestorRecord, TargetRow

logger = logging.getLogger(__name__)

# How much each evidence kind counts toward an investor's score. A live
# portfolio investment is the strongest possible signal; a generic "other"
# mention is the weakest.
_KIND_WEIGHT: dict[str, float] = {
    "portfolio_investment": 1.0,
    "fund_close": 0.8,
    "thesis_publication": 0.6,
    "portfolio_gap": 0.5,
    "exit": 0.5,
    "personnel": 0.4,
    "other": 0.3,
}

_RECENCY_FLOOR = 0.2  # even a two-year-old fact still counts for something
_RECENCY_HALF_LIFE_DAYS = 365

_UNDERFILLED_THRESHOLD = 30
_TIEBREAK_BONUS = 0.01
_SCORE_BUCKET_DECIMALS = 2  # scores within this many decimals are "tied"


# --- public API ---


def score_and_rank(investors: list[InvestorRecord], profile: CompanyProfile, settings: Settings) -> tuple[list[TargetRow], bool]:
    """InvestorRecord list -> ranked, capped TargetRow list.

    Returns (rows, list_underfilled). An investor is dropped if it has
    fewer than MIN_EVIDENCE_PER_INVESTOR records, or if every one of its
    records is stale -- lead_evidence must always be fresh (the guarantee
    we make to the Composio module), and there's nothing fresh to lead with.
    """
    rows = [row for investor in investors if (row := _to_target_row(investor, settings)) is not None]
    rows.sort(key=lambda r: (-round(r.score, _SCORE_BUCKET_DECIMALS), -_tiebreak_bonus(r, profile.founder_context)))

    list_underfilled = len(rows) < _UNDERFILLED_THRESHOLD
    capped = rows[: settings.list_cap]
    for row in capped:
        row.list_underfilled = list_underfilled

    logger.info(
        "scored %d investors -> %d ranked rows (underfilled=%s)", len(investors), len(capped), list_underfilled
    )
    return capped, list_underfilled


# --- private internals ---


def _to_target_row(investor: InvestorRecord, settings: Settings) -> TargetRow | None:
    if len(investor.evidence) < settings.min_evidence_per_investor:
        return None

    fresh_evidence = [e for e in investor.evidence if not e.stale]
    if not fresh_evidence:
        return None  # nothing we can vouch for as the email's opening fact

    sorted_evidence = sorted(investor.evidence, key=_evidence_score, reverse=True)
    lead_evidence = max(fresh_evidence, key=_evidence_score)
    total_score = sum(_evidence_score(e) for e in investor.evidence)

    return TargetRow(
        investor_firm=investor.firm,
        investor_person=investor.person,
        role=investor.role,
        score=total_score,
        evidence=sorted_evidence,
        lead_evidence=lead_evidence,
        contact_email=None,  # resolved by the Composio module
        firm_domain=None,
    )


# --- static helpers ---


def _evidence_score(record: EvidenceRecord) -> float:
    kind_weight = _KIND_WEIGHT.get(record.kind, _KIND_WEIGHT["other"])
    return record.confidence * kind_weight * _recency_factor(record)


def _recency_factor(record: EvidenceRecord) -> float:
    event_date = record.event_date or record.source_published_at
    if event_date is None:
        return _RECENCY_FLOOR
    age_days = max(0, (date.today() - event_date).days)
    decayed = 0.5 ** (age_days / _RECENCY_HALF_LIFE_DAYS)
    return max(_RECENCY_FLOOR, decayed)


def _tiebreak_bonus(row: TargetRow, founder_context: list[str]) -> float:
    if not founder_context:
        return 0.0
    haystack = " ".join(e.claim for e in row.evidence).lower() + " " + (row.investor_person or "").lower()
    return _TIEBREAK_BONUS if any(signal.lower() in haystack for signal in founder_context) else 0.0
