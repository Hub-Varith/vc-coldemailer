"""Stage 5: the freshness pass. This is the product's actual differentiator
(BACKEND_SPEC.md Sec 5.6) -- a database that was accurate six months ago is
not evidence, it's a liability. Every evidence record past its per-kind
staleness threshold gets a targeted re-check against Octen before it's
allowed to reach the founder.
"""

import logging
from datetime import date, datetime, timedelta, timezone

from app.config import Settings
from app.models import EvidenceRecord, InvestorRecord, OctenQuery
from app.octen_client import OctenClient

logger = logging.getLogger(__name__)

# Evidence kinds decay at very different rates -- a personnel change is
# stale in a month, a thesis blog post is still relevant a year later.
_STALENESS_MAX_AGE_DAYS: dict[str, int] = {
    "personnel": 30,
    "fund_close": 180,
    "portfolio_investment": 90,
    "thesis_publication": 365,
    "portfolio_gap": 90,
}


# --- public API ---


async def verify(investors: list[InvestorRecord], settings: Settings, octen_client: OctenClient) -> list[InvestorRecord]:
    """Re-check every evidence record past its staleness threshold. Fresh
    confirmation clears the stale flag; no confirmation leaves it set, so
    the record can still be shown but the scorer will refuse to use it as
    the email's opening fact."""
    for investor in investors:
        for record in investor.evidence:
            await _verify_record(record, settings, octen_client)
    return investors


# --- private internals ---


async def _verify_record(record: EvidenceRecord, settings: Settings, octen_client: OctenClient) -> None:
    max_age_days = _STALENESS_MAX_AGE_DAYS.get(record.kind, settings.freshness_max_age_days)
    age_days = _age_in_days(record)

    if age_days is not None and age_days <= max_age_days:
        record.verified_at = _now()
        record.stale = False
        return

    confirmed = await _reverify_against_octen(record, max_age_days, octen_client)
    record.verified_at = _now()
    record.stale = not confirmed
    if record.stale:
        logger.info("evidence went stale: %s / %s (%s)", record.investor_firm, record.kind, record.source_url)


async def _reverify_against_octen(record: EvidenceRecord, max_age_days: int, octen_client: OctenClient) -> bool:
    """Fire one targeted query scoped to the staleness window. Any result
    coming back counts as fresh confirmation that the fact still holds."""
    query = OctenQuery(
        query=f"{record.investor_firm} {_reverification_phrase(record.kind)}",
        require_text=[record.investor_firm],
        published_after=date.today() - timedelta(days=max_age_days),
        max_results=3,
    )
    results = await octen_client.search(query)
    return len(results) > 0


# --- static helpers ---


def _age_in_days(record: EvidenceRecord) -> int | None:
    event_date = record.event_date or record.source_published_at
    if event_date is None:
        return None
    return (date.today() - event_date).days


def _now() -> datetime:
    return datetime.now(timezone.utc)


_REVERIFICATION_PHRASES: dict[str, str] = {
    "personnel": "team partner",
    "fund_close": "new fund closed",
    "portfolio_investment": "portfolio investment",
    "portfolio_gap": "portfolio",
    "thesis_publication": "thesis",
    "exit": "exit acquisition",
    "other": "",
}


def _reverification_phrase(kind: str) -> str:
    return _REVERIFICATION_PHRASES.get(kind, "")
