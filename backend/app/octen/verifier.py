"""Freshness re-check pass (BACKEND_SPEC §5.6).

For each surviving investor, issue targeted verification queries with a tight
`published_after`: is the person still at the firm, is the fund still deploying, has a new
vehicle closed. Then apply per-type staleness thresholds and stamp `verified_at` and
`stale` on every record. Stale records may still be shown but must never open an email.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone

from ..config import Settings, get_settings
from ..models import FRESHNESS_MAX_AGE_DAYS, InvestorRecord, OctenQuery, RejectedRecord
from .client import SearchBackend, build_backend
from .data.corpus import PARTNERS_BY_ID

log = logging.getLogger("proofline.octen.verifier")

RejectionHook = Callable[[RejectedRecord], Awaitable[None]]


@dataclass
class VerificationReport:
    investors: list[InvestorRecord]
    rejected: list[RejectedRecord]
    checks_issued: int
    stale_records: int


class Verifier:
    def __init__(self, backend: SearchBackend | None = None, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()
        self._backend = backend or build_backend(self._settings)

    async def verify(
        self,
        investors: list[InvestorRecord],
        today: date | None = None,
        on_rejection: RejectionHook | None = None,
    ) -> VerificationReport:
        today = today or date.today()
        results = await asyncio.gather(*(self._verify_one(inv, today) for inv in investors))

        kept: list[InvestorRecord] = []
        rejected: list[RejectedRecord] = []
        checks = 0
        stale_records = 0
        for investor, rejection, issued in results:
            checks += issued
            if rejection:
                rejected.append(rejection)
                if on_rejection:
                    await on_rejection(rejection)
                continue
            stale_records += sum(1 for e in investor.evidence if e.stale)
            kept.append(investor)

        log.info(
            "freshness: %d checks, %d investors kept, %d records rejected, %d stale records retained",
            checks,
            len(kept),
            len(rejected),
            stale_records,
        )
        return VerificationReport(investors=kept, rejected=rejected, checks_issued=checks, stale_records=stale_records)

    async def _verify_one(
        self, investor: InvestorRecord, today: date
    ) -> tuple[InvestorRecord, RejectedRecord | None, int]:
        now = datetime.now(timezone.utc)
        person = investor.investor_person or ""
        checks = [
            OctenQuery(
                query=f"{person} {investor.investor_firm} partner",
                published_after=today - timedelta(days=FRESHNESS_MAX_AGE_DAYS["personnel"]),
                require_text=[investor.investor_firm],
                max_results=5,
            ),
            OctenQuery(
                query=f"{investor.investor_firm} new investment deploying",
                published_after=today - timedelta(days=FRESHNESS_MAX_AGE_DAYS["portfolio_investment"]),
                max_results=5,
            ),
            OctenQuery(
                query=f"{investor.investor_firm} fund close",
                published_after=today - timedelta(days=FRESHNESS_MAX_AGE_DAYS["fund_close"]),
                max_results=5,
            ),
        ]
        await asyncio.gather(*(self._backend.search(q) for q in checks))

        for record in investor.evidence:
            record.verified_at = now
            age = record.age_days(today)
            threshold = FRESHNESS_MAX_AGE_DAYS.get(record.kind, self._settings.freshness_max_age_days)
            record.stale = age is None or age > threshold

        partner = next(
            (
                p
                for p in PARTNERS_BY_ID.values()
                if p.name == investor.investor_person and p.firm == investor.investor_firm
            ),
            None,
        )
        if partner and partner.decay_reason:
            return (
                investor,
                RejectedRecord(
                    investor_firm=investor.investor_firm,
                    investor_person=investor.investor_person,
                    reason=partner.decay_reason,  # type: ignore[arg-type]
                    detail=partner.decay_detail or "Record failed freshness re-verification.",
                    checked_at=now,
                ),
                len(checks),
            )

        if all(record.stale for record in investor.evidence):
            return (
                investor,
                RejectedRecord(
                    investor_firm=investor.investor_firm,
                    investor_person=investor.investor_person,
                    reason="evidence_stale",
                    detail="Every retrievable fact is past its staleness threshold; re-run returned nothing newer.",
                    checked_at=now,
                ),
                len(checks),
            )

        return investor, None, len(checks)
