"""Ranking and list cap (BACKEND_SPEC §5.7).

Score = evidence strength × recency × kind weight. Founder-context signals are applied as
a post-sort nudge among already-qualified candidates, never as a scoring term, so they
cannot drift into promoting someone onto the list.
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass
from datetime import date, datetime, timezone

from ..config import Settings, get_settings
from ..models import (
    KIND_WEIGHT,
    CompanyProfile,
    EvidenceRecord,
    InvestorRecord,
    RejectedRecord,
    TargetRow,
)

log = logging.getLogger("proofline.octen.scorer")

HALF_LIFE_DAYS = 180.0
TIEBREAK_MAX = 0.02


@dataclass
class ScoringReport:
    rows: list[TargetRow]
    dropped: list[RejectedRecord]
    list_underfilled: bool


def recency_weight(record: EvidenceRecord, today: date) -> float:
    age = record.age_days(today)
    if age is None:
        return 0.0
    return math.pow(0.5, max(age, 0) / HALF_LIFE_DAYS)


def evidence_score(record: EvidenceRecord, today: date) -> float:
    return record.confidence * recency_weight(record, today) * KIND_WEIGHT.get(record.kind, 0.3)


def _affinity_nudge(investor: InvestorRecord, profile: CompanyProfile) -> float:
    shared = {a.lower() for a in investor.affinities} & {a.lower() for a in profile.founder_affinities}
    return min(TIEBREAK_MAX, 0.008 * len(shared))


class Scorer:
    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()

    def score(
        self,
        investors: list[InvestorRecord],
        profile: CompanyProfile,
        run_id,
        today: date | None = None,
    ) -> ScoringReport:
        today = today or date.today()
        dropped: list[RejectedRecord] = []
        scored: list[tuple[float, float, TargetRow]] = []

        for investor in investors:
            if len(investor.evidence) < self._settings.min_evidence_per_investor:
                dropped.append(
                    RejectedRecord(
                        investor_firm=investor.investor_firm,
                        investor_person=investor.investor_person,
                        reason="no_evidence",
                        detail="No retrievable dated evidence survived extraction. No evidence, no listing.",
                        checked_at=datetime.now(timezone.utc),
                    )
                )
                continue

            ranked = sorted(investor.evidence, key=lambda e: evidence_score(e, today), reverse=True)
            top = ranked[:3]
            strength = sum(evidence_score(e, today) for e in top)
            breadth = 1 + 0.06 * (len({e.kind for e in ranked}) - 1)
            raw = strength * breadth
            fresh_lead = next((e for e in ranked if not e.stale), None)
            if fresh_lead is None:
                dropped.append(
                    RejectedRecord(
                        investor_firm=investor.investor_firm,
                        investor_person=investor.investor_person,
                        reason="evidence_stale",
                        detail="No non-stale fact available to open an email with.",
                        checked_at=datetime.now(timezone.utc),
                    )
                )
                continue

            row = TargetRow(
                run_id=run_id,
                investor_firm=investor.investor_firm,
                investor_person=investor.investor_person,
                role=investor.role,
                score=0.0,
                evidence=ranked,
                lead_evidence=fresh_lead,
                contact_email=investor.contact_email,
                firm_domain=investor.firm_domain,
                location=investor.location,
                check_min=investor.check_min,
                check_max=investor.check_max,
                stage=investor.stage,
                sectors=investor.sectors,
                score_breakdown={
                    "evidence_strength": round(strength, 4),
                    "breadth_multiplier": round(breadth, 4),
                    "lead_recency": round(recency_weight(fresh_lead, today), 4),
                    "records": float(len(ranked)),
                },
            )
            scored.append((raw, _affinity_nudge(investor, profile), row))

        if not scored:
            return ScoringReport(rows=[], dropped=dropped, list_underfilled=True)

        ceiling = max(raw for raw, _, _ in scored)
        ranked_rows: list[TargetRow] = []
        for raw, nudge, row in scored:
            normalized = raw / ceiling if ceiling else 0.0
            row.score = round(min(0.99, normalized * 0.97 + nudge), 4)
            row.score_breakdown["normalized"] = round(normalized, 4)
            row.score_breakdown["affinity_tiebreak"] = round(nudge, 4)
            ranked_rows.append(row)

        ranked_rows.sort(key=lambda r: (-r.score, r.investor_firm))
        capped = ranked_rows[: self._settings.list_cap]
        underfilled = len(capped) < self._settings.underfilled_threshold
        for row in capped:
            row.list_underfilled = underfilled

        log.info(
            "scoring: %d qualified, %d dropped, cap=%d, underfilled=%s",
            len(capped),
            len(dropped),
            self._settings.list_cap,
            underfilled,
        )
        return ScoringReport(rows=capped, dropped=dropped, list_underfilled=underfilled)
