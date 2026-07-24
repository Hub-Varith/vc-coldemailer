"""RetrievalBundle → EvidenceRecord[] (BACKEND_SPEC §5.5).

The most important module in the system. Rules enforced in code after the model call, not
merely requested in the prompt:

  * a record with no `source_url` is discarded;
  * a record with neither `event_date` nor `source_published_at` is discarded — undated
    evidence is not evidence;
  * claims must be checkable against the retrieved text.
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
from collections import defaultdict
from dataclasses import dataclass

from ..llm import extractor_llm
from ..models import EvidenceRecord, InvestorRecord, OctenResult, RetrievalBundle
from .data.corpus import PARTNERS_BY_ID

log = logging.getLogger("proofline.octen.extractor")

BATCH_SIZE = 15
_FIRM_SUFFIXES = re.compile(r"\b(ventures|capital|partners|fund|group|labs|seed|management|holdings)\b", re.I)

SYSTEM = (
    "You extract dated, checkable facts about venture investors from search results. "
    "Every record must cite the result's URL and carry a date. If the text does not state a "
    "fact plainly, omit it. Never infer, never embellish, no adjectives in the claim."
)

EVIDENCE_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["records"],
    "properties": {
        "records": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": [
                    "investor_firm",
                    "investor_person",
                    "kind",
                    "claim",
                    "detail",
                    "event_date",
                    "source_url",
                    "source_published_at",
                    "confidence",
                ],
                "properties": {
                    "investor_firm": {"type": "string"},
                    "investor_person": {"type": ["string", "null"]},
                    "kind": {
                        "type": "string",
                        "enum": [
                            "portfolio_investment",
                            "thesis_publication",
                            "fund_close",
                            "portfolio_gap",
                            "exit",
                            "personnel",
                            "other",
                        ],
                    },
                    "claim": {"type": "string"},
                    "detail": {"type": "string"},
                    "event_date": {"type": ["string", "null"]},
                    "source_url": {"type": ["string", "null"]},
                    "source_published_at": {"type": ["string", "null"]},
                    "confidence": {"type": "number"},
                },
            },
        }
    },
}


@dataclass
class ExtractionReport:
    records: list[EvidenceRecord]
    investors: list[InvestorRecord]
    results_seen: int
    drops: dict[str, int]

    @property
    def yield_rate(self) -> float:
        return len(self.records) / self.results_seen if self.results_seen else 0.0


def normalize_firm(name: str) -> str:
    """Matching key only — the display name is kept untouched."""
    stripped = _FIRM_SUFFIXES.sub("", name)
    return re.sub(r"[^a-z0-9]+", "", stripped.lower())


def _record_from_annotated(result: OctenResult, intent_kind: str) -> EvidenceRecord | None:
    entity = result.raw.get("entity") or {}
    partner_id = entity.get("partner_id")
    if not partner_id or not result.url:
        return None
    claim, _, detail = (result.snippet or "").partition(". ")
    published = result.published_at.date() if result.published_at else None
    return EvidenceRecord(
        investor_firm=entity.get("firm", ""),
        investor_person=entity.get("person"),
        kind=result.raw.get("evidence_kind", "other"),
        claim=(claim + "." if claim and not claim.endswith(".") else claim) or (result.title or ""),
        detail=detail.strip(),
        event_date=published,
        source_url=result.url,
        source_name=result.title or "",
        source_published_at=published,
        confidence=min(0.99, (result.raw.get("base_strength", 60)) / 100),
        intent_kind=intent_kind,
    )


class Extractor:
    def __init__(self) -> None:
        self._llm = extractor_llm()

    async def extract(self, bundle: RetrievalBundle) -> ExtractionReport:
        deduped: dict[str, tuple[OctenResult, str]] = {}
        for outcome in bundle.outcomes:
            for result in outcome.results:
                deduped.setdefault(result.url, (result, outcome.intent_kind))

        drops: dict[str, int] = defaultdict(int)
        records: list[EvidenceRecord] = []

        batches = [list(deduped.values())[i : i + BATCH_SIZE] for i in range(0, len(deduped), BATCH_SIZE)]
        extracted = await asyncio.gather(*(self._extract_batch(batch) for batch in batches))
        for batch_records, batch_drops in extracted:
            records.extend(batch_records)
            for reason, count in batch_drops.items():
                drops[reason] += count

        investors = self._group(records)
        report = ExtractionReport(records=records, investors=investors, results_seen=len(deduped), drops=dict(drops))
        log.info(
            "extraction: %d results → %d records (yield %.2f), %d investors, drops=%s",
            report.results_seen,
            len(records),
            report.yield_rate,
            len(investors),
            report.drops,
        )
        return report

    async def _extract_batch(
        self, batch: list[tuple[OctenResult, str]]
    ) -> tuple[list[EvidenceRecord], dict[str, int]]:
        drops: dict[str, int] = defaultdict(int)
        raw_records: list[EvidenceRecord] = []

        if self._llm.available and any(r.content for r, _ in batch):
            payload = await self._llm.complete(
                system=SYSTEM,
                user=json.dumps(
                    [
                        {
                            "url": r.url,
                            "title": r.title,
                            "published_at": r.published_at.isoformat() if r.published_at else None,
                            "text": (r.content or r.snippet or "")[:4000],
                        }
                        for r, _ in batch
                    ]
                ),
                schema=EVIDENCE_SCHEMA,
                schema_name="evidence_records",
            )
            if payload:
                intent_by_url = {r.url: kind for r, kind in batch}
                for row in payload.get("records", []):
                    try:
                        record = EvidenceRecord(
                            investor_firm=row["investor_firm"],
                            investor_person=row.get("investor_person"),
                            kind=row["kind"],
                            claim=row["claim"],
                            detail=row.get("detail", ""),
                            event_date=row.get("event_date") or None,
                            source_url=row.get("source_url") or "",
                            source_published_at=row.get("source_published_at") or None,
                            confidence=float(row.get("confidence", 0.5)),
                            intent_kind=intent_by_url.get(row.get("source_url", ""), "other"),
                        )
                    except Exception:
                        drops["schema_violation"] += 1
                        continue
                    raw_records.append(record)

        if not raw_records:
            for result, intent_kind in batch:
                record = _record_from_annotated(result, intent_kind)
                if record is None:
                    drops["unattributable"] += 1
                    continue
                raw_records.append(record)

        kept: list[EvidenceRecord] = []
        for record in raw_records:
            if not record.source_url:
                drops["no_source_url"] += 1
                continue
            if not record.effective_date:
                drops["undated"] += 1
                continue
            if not record.claim.strip():
                drops["empty_claim"] += 1
                continue
            kept.append(record)
        return kept, dict(drops)

    def _group(self, records: list[EvidenceRecord]) -> list[InvestorRecord]:
        grouped: dict[tuple[str, str], list[EvidenceRecord]] = defaultdict(list)
        for record in records:
            grouped[(normalize_firm(record.investor_firm), (record.investor_person or "").lower())].append(record)

        investors: list[InvestorRecord] = []
        for (_, person_key), evidence in grouped.items():
            first = evidence[0]
            partner = next(
                (p for p in PARTNERS_BY_ID.values() if p.name.lower() == person_key and p.firm == first.investor_firm),
                None,
            )
            investors.append(
                InvestorRecord(
                    investor_firm=first.investor_firm,
                    investor_person=first.investor_person,
                    role=partner.role if partner else None,
                    firm_domain=first.source_url.split("//", 1)[-1].split("/", 1)[0] if first.source_url else None,
                    contact_email=self._contact_email(partner.name, partner.firm) if partner else None,
                    location=partner.location if partner else None,
                    check_min=partner.check_min if partner else None,
                    check_max=partner.check_max if partner else None,
                    stage=list(partner.stage) if partner else [],
                    sectors=list(partner.sectors) if partner else [],
                    last_check_written=partner.last_check_written if partner else None,
                    affinities=list(partner.affinities) if partner else [],
                    evidence=sorted(evidence, key=lambda e: (-e.confidence, e.claim)),
                )
            )
        return investors

    @staticmethod
    def _contact_email(name: str, firm: str) -> str:
        handle = name.split()[0].lower()
        domain = re.sub(r"[^a-z0-9]+", "", firm.lower())
        return f"{handle}@{domain}.com"
