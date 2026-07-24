"""Offline retrieval index over the bundled corpus.

Behaves like a search engine: tokenised matching against document text and tags, honours
`published_after` and `require_text`, returns ranked `OctenResult` objects. Swapping in the
real Octen client changes nothing downstream.
"""

from __future__ import annotations

import re
from datetime import datetime, time, timezone

from ..models import OctenQuery, OctenResult
from .data.corpus import DOCUMENTS, PARTNERS_BY_ID, SourceDocument

_TOKEN = re.compile(r"[a-z0-9&]+")
_STOP = {
    "the", "a", "an", "and", "or", "of", "in", "on", "for", "to", "with", "at", "by",
    "vc", "fund", "firm", "investor", "investors", "startup", "startups", "2026", "2025",
}


def _tokens(text: str) -> set[str]:
    return {t for t in _TOKEN.findall(text.lower()) if t not in _STOP and len(t) > 2}


def _doc_text(doc: SourceDocument) -> str:
    partner = PARTNERS_BY_ID[doc.partner_id]
    return " ".join(
        [partner.name, partner.firm, partner.role, partner.location, doc.claim, doc.detail, doc.source_name, *doc.tags]
    )


def _domain(url: str) -> str:
    return url.split("//", 1)[-1].split("/", 1)[0].lower()


class LocalIndex:
    def __init__(self, documents: tuple[SourceDocument, ...] = DOCUMENTS) -> None:
        self._documents = documents
        self._tokens = {doc.id: _tokens(_doc_text(doc)) for doc in documents}
        self._text = {doc.id: _doc_text(doc).lower() for doc in documents}

    def search(self, query: OctenQuery) -> list[OctenResult]:
        wanted = _tokens(query.query)
        if not wanted:
            return []
        scored: list[tuple[float, SourceDocument]] = []
        for doc in self._documents:
            if query.published_after and doc.published < query.published_after:
                continue
            haystack = self._text[doc.id]
            if query.require_text and not all(t.lower() in haystack for t in query.require_text):
                continue
            domain = _domain(doc.source_url)
            if query.include_domains and not any(d in domain for d in query.include_domains):
                continue
            if query.exclude_domains and any(d in domain for d in query.exclude_domains):
                continue
            overlap = wanted & self._tokens[doc.id]
            if not overlap:
                continue
            phrase_bonus = 0.35 if any(tag in query.query.lower() for tag in doc.tags) else 0.0
            score = len(overlap) / len(wanted) + phrase_bonus
            if score < 0.34:
                continue
            scored.append((score, doc))

        scored.sort(key=lambda pair: (-pair[0], -pair[1].base_strength))
        return [self._to_result(doc, score, query) for score, doc in scored[: query.max_results]]

    def _to_result(self, doc: SourceDocument, score: float, query: OctenQuery) -> OctenResult:
        partner = PARTNERS_BY_ID[doc.partner_id]
        published = datetime.combine(doc.published, time(9, 0), tzinfo=timezone.utc)
        raw = {
            "url": doc.source_url,
            "title": doc.source_name,
            "snippet": f"{doc.claim} {doc.detail}",
            "published_date": published.isoformat(),
            "relevance": round(score, 3),
            # Structured annotations the local index can serve directly; the LLM extractor
            # derives the same fields from `content` when running against live Octen.
            "entity": {
                "partner_id": partner.id,
                "person": partner.name,
                "firm": partner.firm,
                "role": partner.role,
            },
            "evidence_kind": doc.kind,
            "base_strength": doc.base_strength,
            "tags": list(doc.tags),
        }
        return OctenResult(
            url=doc.source_url,
            title=doc.source_name,
            snippet=f"{doc.claim} {doc.detail}",
            content=f"{doc.claim}\n\n{doc.detail}" if query.extract_content else None,
            published_at=published,
            crawled_at=datetime.now(timezone.utc),
            raw=raw,
        )
