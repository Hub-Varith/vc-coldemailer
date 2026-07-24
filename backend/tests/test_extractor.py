"""M3: confirms the two hard discard rules (no source_url, no date) are
enforced in code regardless of what the model returns, and that surviving
records get grouped into InvestorRecords."""

from datetime import date
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

from app.config import Settings
from app.extractor import _ExtractionSchema, extract, _normalize_firm_name
from app.models import EvidenceRecord, OctenResult, RetrievalBundle, RetrievalStats, RetrievedResult


def _retrieved(url: str) -> RetrievedResult:
    return RetrievedResult(
        result=OctenResult(url=url, title="t", snippet="s", raw={}),
        intent_kind="adjacent_portfolio",
        query="q",
    )


def _bundle(urls: list[str]) -> RetrievalBundle:
    stats = RetrievalStats(query_count=1, result_count=len(urls), failed_query_count=0, wall_time_s=0.1)
    return RetrievalBundle(profile_id=uuid4(), results=[_retrieved(u) for u in urls], stats=stats)


def _fake_client(records: list[EvidenceRecord]) -> AsyncMock:
    parsed = _ExtractionSchema(records=records)
    response = SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(parsed=parsed))])
    client = AsyncMock()
    client.chat.completions.parse.return_value = response
    return client


def _valid_record(**overrides) -> EvidenceRecord:
    defaults = dict(
        investor_firm="Acme Ventures",
        investor_person="Jane Doe",
        kind="portfolio_investment",
        claim="Acme Ventures backed a hearing startup.",
        event_date=date(2026, 3, 12),
        source_url="https://real.example.com/a",
        source_published_at=None,
        confidence=0.9,
    )
    defaults.update(overrides)
    return EvidenceRecord(**defaults)


async def test_extract_drops_record_with_hallucinated_source_url(monkeypatch):
    monkeypatch.setenv("OPENAI_MODEL_EXTRACTOR", "test-model")
    bundle = _bundle(["https://real.example.com/a"])
    bad = _valid_record(source_url="https://not-in-batch.example.com/x")
    client = _fake_client([bad])
    settings = Settings()

    investors = await extract(bundle, settings, client=client)

    assert investors == []


async def test_extract_drops_record_with_no_dates(monkeypatch):
    monkeypatch.setenv("OPENAI_MODEL_EXTRACTOR", "test-model")
    bundle = _bundle(["https://real.example.com/a"])
    bad = _valid_record(event_date=None, source_published_at=None)
    client = _fake_client([bad])
    settings = Settings()

    investors = await extract(bundle, settings, client=client)

    assert investors == []


async def test_extract_keeps_valid_record_and_groups_by_investor(monkeypatch):
    monkeypatch.setenv("OPENAI_MODEL_EXTRACTOR", "test-model")
    bundle = _bundle(["https://real.example.com/a"])
    good = _valid_record()
    client = _fake_client([good])
    settings = Settings()

    investors = await extract(bundle, settings, client=client)

    assert len(investors) == 1
    assert investors[0].firm == "Acme Ventures"
    assert investors[0].firm_normalized == "acme"
    assert investors[0].person == "Jane Doe"
    assert investors[0].evidence == [good]


def test_normalize_firm_name_strips_known_suffixes():
    assert _normalize_firm_name("Acme Ventures") == "acme"
    assert _normalize_firm_name("Acme Capital Partners") == "acme"
    assert _normalize_firm_name("Sequoia") == "sequoia"
