"""The rules that stop this from becoming another generic database."""

from datetime import date, datetime, timedelta, timezone

import pytest

from app.models import EvidenceRecord, InvestorRecord, OctenResult
from app.octen.extractor import Extractor, normalize_firm
from app.octen.scorer import Scorer, evidence_score
from app.octen.verifier import Verifier
from uuid import uuid4


def _record(**overrides) -> EvidenceRecord:
    base = dict(
        investor_firm="Northstar Ventures",
        investor_person="Maya Chen",
        kind="thesis_publication",
        claim="Published a thesis on hearing infrastructure.",
        source_url="https://northstar.vc/notes/the-quiet-market",
        event_date=date(2026, 5, 14),
        confidence=0.9,
    )
    base.update(overrides)
    return EvidenceRecord(**base)


@pytest.mark.asyncio
async def test_record_without_source_url_is_discarded():
    extractor = Extractor()
    result = OctenResult(url="", title="t", snippet="A claim. Some detail.", raw={})
    kept, drops = await extractor._extract_batch([(result, "thesis_signal")])
    assert kept == []
    assert drops


@pytest.mark.asyncio
async def test_undated_record_is_discarded():
    extractor = Extractor()
    undated = OctenResult(
        url="https://example.com/a",
        title="t",
        snippet="A claim. Some detail.",
        published_at=None,
        raw={"entity": {"partner_id": "maya-chen", "person": "Maya Chen", "firm": "Northstar Ventures"}},
    )
    kept, drops = await extractor._extract_batch([(undated, "thesis_signal")])
    assert kept == [], "undated evidence is not evidence"
    assert drops.get("undated") == 1


@pytest.mark.asyncio
async def test_dated_attributable_record_survives(annotated_results):
    extractor = Extractor()
    kept, _ = await extractor._extract_batch([(r, "thesis_signal") for r in annotated_results])
    assert kept, "well-formed results produce evidence"
    assert all(r.source_url and r.effective_date for r in kept)


def test_firm_normalization_matches_variants_but_keeps_display_name():
    assert normalize_firm("Northstar Ventures") == normalize_firm("Northstar")
    assert normalize_firm("Kettle & Vane") == normalize_firm("Kettle & Vane Capital")
    assert normalize_firm("Overture Capital") != normalize_firm("Northstar Ventures")


@pytest.mark.asyncio
async def test_staleness_thresholds_are_per_kind():
    today = date(2026, 7, 23)
    investor = InvestorRecord(
        investor_firm="Northstar Ventures",
        investor_person="Maya Chen",
        evidence=[
            _record(kind="thesis_publication", event_date=today - timedelta(days=300)),
            _record(kind="portfolio_investment", event_date=today - timedelta(days=100)),
            _record(kind="personnel", event_date=today - timedelta(days=20)),
        ],
    )
    report = await Verifier().verify([investor], today=today)
    kept = report.investors[0]

    assert kept.evidence[0].stale is False, "a thesis is fresh for 365 days"
    assert kept.evidence[1].stale is True, "a portfolio investment goes stale at 90 days"
    assert kept.evidence[2].stale is False, "personnel is fresh inside 30 days"
    assert all(e.verified_at is not None for e in kept.evidence)


@pytest.mark.asyncio
async def test_departed_partner_is_rejected_by_the_freshness_gate():
    investor = InvestorRecord(
        investor_firm="Beacon Row",
        investor_person="Arjun Mehta",
        evidence=[_record(investor_firm="Beacon Row", investor_person="Arjun Mehta", event_date=date(2026, 6, 1))],
    )
    report = await Verifier().verify([investor], today=date(2026, 7, 23))
    assert report.investors == []
    assert report.rejected[0].reason == "partner_departed"


def test_investor_without_evidence_is_dropped_not_scored_low(profile):
    empty = InvestorRecord(investor_firm="Ghost Capital", investor_person="Nobody", evidence=[])
    report = Scorer().score([empty], profile, uuid4(), today=date(2026, 7, 23))
    assert report.rows == []
    assert report.dropped[0].reason == "no_evidence"


def test_lead_evidence_is_never_stale(profile):
    today = date(2026, 7, 23)
    investor = InvestorRecord(
        investor_firm="Northstar Ventures",
        investor_person="Maya Chen",
        evidence=[
            _record(kind="portfolio_investment", event_date=today - timedelta(days=400), stale=True, confidence=0.99),
            _record(kind="thesis_publication", event_date=today - timedelta(days=30), stale=False, confidence=0.7),
        ],
    )
    report = Scorer().score([investor], profile, uuid4(), today=today)
    assert report.rows[0].lead_evidence.stale is False


def test_recency_beats_raw_confidence_at_equal_kind():
    today = date(2026, 7, 23)
    fresh = _record(event_date=today - timedelta(days=10), confidence=0.7)
    old = _record(event_date=today - timedelta(days=700), confidence=0.95)
    assert evidence_score(fresh, today) > evidence_score(old, today)


def test_affinity_is_a_tiebreak_and_cannot_promote(profile):
    today = date(2026, 7, 23)
    strong = InvestorRecord(
        investor_firm="Overture Capital",
        investor_person="Elias Lind",
        evidence=[_record(kind="thesis_publication", event_date=today - timedelta(days=10), confidence=0.95)],
    )
    weak_but_affiliated = InvestorRecord(
        investor_firm="Halden Ventures",
        investor_person="Lena Fischer",
        affinities=["Lisbon", "IST"],
        evidence=[_record(kind="other", event_date=today - timedelta(days=300), confidence=0.4)],
    )
    report = Scorer().score([weak_but_affiliated, strong], profile, uuid4(), today=today)
    assert [r.investor_person for r in report.rows] == ["Elias Lind", "Lena Fischer"]
    assert report.rows[1].score_breakdown["affinity_tiebreak"] <= 0.02


def test_underfilled_list_is_flagged(profile):
    today = date(2026, 7, 23)
    investors = [
        InvestorRecord(
            investor_firm=f"Firm {i}",
            investor_person=f"Partner {i}",
            evidence=[_record(event_date=today - timedelta(days=5))],
        )
        for i in range(5)
    ]
    report = Scorer().score(investors, profile, uuid4(), today=today)
    assert report.list_underfilled is True
    assert all(row.list_underfilled for row in report.rows)


def test_verified_at_is_timezone_aware():
    record = _record(verified_at=datetime.now(timezone.utc))
    assert record.verified_at is not None and record.verified_at.tzinfo is not None
