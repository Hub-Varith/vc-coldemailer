"""Stage 4: turn raw Octen results into dated, attributable evidence.

This is the most important module in the system (BACKEND_SPEC.md Sec 5.5) --
it's the step that turns "a database says this fund is seed/medtech" into
"this fund backed a company like ours, three weeks ago, source attached".
The two hard discard rules below are what stop this from becoming another
generic database and are enforced in code, not just prompted for.
"""

import asyncio
import logging

from openai import AsyncOpenAI
from pydantic import BaseModel

from app.config import Settings
from app.models import EvidenceRecord, InvestorRecord, RetrievalBundle, RetrievedResult
from app.openai_client import get_extractor_model, get_openai

logger = logging.getLogger(__name__)

_BATCH_SIZE = 15

_SYSTEM_PROMPT = """\
You extract structured, dated evidence about investors from search results.

For each result, decide whether it contains a checkable fact about a \
specific investor or firm relevant to funding a company (a portfolio \
investment, a thesis publication, a fund close, a portfolio gap, an exit, \
or a personnel change). If it does, emit one evidence record per fact.

Rules:
- Every record MUST cite the source_url of the result it came from. Never \
invent or guess a URL.
- The claim must be one factual sentence, checkable against the source \
text. Do not infer beyond what the text states. No adjectives, no spin.
- If a result contains no checkable investor fact, emit nothing for it.
- confidence is 0-1: how directly the source text supports the claim.
"""


class _ExtractionSchema(BaseModel):
    records: list[EvidenceRecord]


# --- public API ---


async def extract(bundle: RetrievalBundle, settings: Settings, client: AsyncOpenAI | None = None) -> list[InvestorRecord]:
    """RetrievalBundle -> grouped, deduped InvestorRecord list.

    Batches results (10-20 per call, per spec) and extracts concurrently
    under OPENAI_MAX_CONCURRENCY. A malformed batch is retried once, then
    dropped and logged -- one bad batch never poisons the whole run.
    """
    openai_client = client or get_openai()
    batches = _batch(bundle.results, _BATCH_SIZE)
    semaphore = asyncio.Semaphore(settings.openai_max_concurrency)

    async def _run_batch(batch: list[RetrievedResult]) -> list[EvidenceRecord]:
        async with semaphore:
            return await _extract_batch(batch, openai_client)

    batch_results = await asyncio.gather(*(_run_batch(b) for b in batches))
    all_records = [record for records in batch_results for record in records]

    logger.info(
        "extraction done for profile=%s: %d results -> %d evidence records (yield=%.2f)",
        bundle.profile_id, len(bundle.results), len(all_records),
        len(all_records) / len(bundle.results) if bundle.results else 0.0,
    )
    return _group_by_investor(all_records)


# --- private internals ---


async def _extract_batch(batch: list[RetrievedResult], client: AsyncOpenAI) -> list[EvidenceRecord]:
    valid_urls = {item.result.url for item in batch}
    user_content = _format_batch_for_prompt(batch)

    for attempt in (1, 2):
        try:
            response = await client.chat.completions.parse(
                model=get_extractor_model(),
                temperature=0.0,
                messages=[
                    {"role": "system", "content": _SYSTEM_PROMPT},
                    {"role": "user", "content": user_content},
                ],
                response_format=_ExtractionSchema,
            )
            parsed = response.choices[0].message.parsed
            assert parsed is not None
            return [r for r in parsed.records if _passes_discard_rules(r, valid_urls)]
        except Exception as exc:  # schema violation, API error -- one retry then drop
            if attempt == 2:
                logger.warning("extraction batch dropped after retry: %s", exc)
                return []
            logger.info("extraction batch failed, retrying once: %s", exc)
    return []


def _passes_discard_rules(record: EvidenceRecord, valid_urls: set[str]) -> bool:
    if not record.source_url or record.source_url not in valid_urls:
        return False
    if record.event_date is None and record.source_published_at is None:
        return False
    return True


def _group_by_investor(records: list[EvidenceRecord]) -> list[InvestorRecord]:
    """Group evidence by (normalized firm, person) -- a specific partner and
    a fund-level fact with no named person are treated as distinct
    investors, since outreach targets a person where one is known."""
    groups: dict[tuple[str, str | None], InvestorRecord] = {}
    for record in records:
        firm_normalized = _normalize_firm_name(record.investor_firm)
        key = (firm_normalized, record.investor_person)
        if key not in groups:
            groups[key] = InvestorRecord(
                firm=record.investor_firm,
                firm_normalized=firm_normalized,
                person=record.investor_person,
                role=None,
                evidence=[],
            )
        groups[key].evidence.append(record)
    return list(groups.values())


# --- static helpers ---


def _format_batch_for_prompt(batch: list[RetrievedResult]) -> str:
    lines = []
    for item in batch:
        r = item.result
        lines.append(
            f"url: {r.url}\n"
            f"intent: {item.intent_kind}\n"
            f"title: {r.title or ''}\n"
            f"published_at: {r.published_at.date().isoformat() if r.published_at else 'unknown'}\n"
            f"text: {r.content or r.snippet or ''}\n"
        )
    return "\n---\n".join(lines)


_FIRM_SUFFIXES = ("ventures", "capital", "partners", "fund", "vc", "llc", "lp")


def _normalize_firm_name(name: str) -> str:
    """"Acme Ventures" -> "acme". Used for grouping/dedupe only; the
    original display name is preserved on the record."""
    words = [w for w in name.lower().replace(",", "").split() if w not in _FIRM_SUFFIXES]
    return " ".join(words).strip()


def _batch(items: list[RetrievedResult], size: int) -> list[list[RetrievedResult]]:
    return [items[i : i + size] for i in range(0, len(items), size)]
