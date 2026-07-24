"""M4: confirms per-kind staleness thresholds are respected and that a
missing re-confirmation from Octen sets stale=True without dropping the
record."""

from datetime import date, timedelta
from unittest.mock import AsyncMock

from app.config import Settings
from app.models import EvidenceRecord, InvestorRecord, OctenResult
from app.verifier import verify


def _investor(**evidence_overrides) -> InvestorRecord:
    defaults = dict(
        investor_firm="Acme Ventures",
        investor_person="Jane Doe",
        kind="personnel",
        claim="Jane Doe is a partner at Acme.",
        event_date=date.today() - timedelta(days=60),  # older than the 30-day personnel threshold
        source_url="https://example.com/a",
        source_published_at=None,
        confidence=0.8,
    )
    defaults.update(evidence_overrides)
    record = EvidenceRecord(**defaults)
    return InvestorRecord(firm="Acme Ventures", firm_normalized="acme", person="Jane Doe", role=None, evidence=[record])


async def test_stale_record_gets_reverified_and_marked_stale_when_no_confirmation():
    investor = _investor()
    settings = Settings()
    octen_client = AsyncMock()
    octen_client.search.return_value = []  # no fresh confirmation found

    result = await verify([investor], settings, octen_client)

    record = result[0].evidence[0]
    assert record.stale is True
    assert record.verified_at is not None
    octen_client.search.assert_awaited_once()


async def test_stale_record_cleared_when_reverification_confirms():
    investor = _investor()
    settings = Settings()
    octen_client = AsyncMock()
    octen_client.search.return_value = [OctenResult(url="https://fresh.example.com", raw={})]

    result = await verify([investor], settings, octen_client)

    assert result[0].evidence[0].stale is False


async def test_fresh_record_skips_reverification_entirely():
    investor = _investor(event_date=date.today())  # well within the 30-day threshold
    settings = Settings()
    octen_client = AsyncMock()

    result = await verify([investor], settings, octen_client)

    assert result[0].evidence[0].stale is False
    octen_client.search.assert_not_awaited()
