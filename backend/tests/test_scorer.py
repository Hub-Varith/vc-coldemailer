"""M4: confirms an investor with only stale evidence is dropped (lead
evidence must be fresh), a thin investor below the evidence floor is
dropped, and the founder-context tiebreaker never promotes a low scorer
above a clearly stronger one."""

from datetime import date
from uuid import uuid4

from app.config import Settings
from app.models import CompanyProfile, EvidenceRecord, InvestorRecord
from app.scorer import score_and_rank


def _evidence(**overrides) -> EvidenceRecord:
    defaults = dict(
        investor_firm="Acme Ventures",
        investor_person="Jane Doe",
        kind="portfolio_investment",
        claim="Acme backed a hearing startup.",
        event_date=date.today(),
        source_url="https://example.com/a",
        source_published_at=None,
        confidence=0.9,
        stale=False,
    )
    defaults.update(overrides)
    return EvidenceRecord(**defaults)


def _profile(**overrides) -> CompanyProfile:
    defaults = dict(
        id=uuid4(),
        company_name="Test Co",
        one_liner="x",
        sector="medtech",
        product_description="x",
        stage="seed",
        geography="US",
    )
    defaults.update(overrides)
    return CompanyProfile(**defaults)


def test_investor_with_only_stale_evidence_is_dropped():
    investor = InvestorRecord(
        firm="Acme Ventures", firm_normalized="acme", person="Jane Doe", role=None,
        evidence=[_evidence(stale=True)],
    )
    rows, _ = score_and_rank([investor], _profile(), Settings())
    assert rows == []


def test_investor_below_min_evidence_is_dropped():
    investor = InvestorRecord(firm="Acme Ventures", firm_normalized="acme", person=None, role=None, evidence=[])
    rows, _ = score_and_rank([investor], _profile(), Settings(min_evidence_per_investor=1))
    assert rows == []


def test_stronger_investor_ranks_above_weaker_investor():
    strong = InvestorRecord(
        firm="Strong Ventures", firm_normalized="strong", person=None, role=None,
        evidence=[_evidence(investor_firm="Strong Ventures", confidence=1.0, kind="portfolio_investment")],
    )
    weak = InvestorRecord(
        firm="Weak Ventures", firm_normalized="weak", person=None, role=None,
        evidence=[_evidence(investor_firm="Weak Ventures", confidence=0.2, kind="other")],
    )
    rows, underfilled = score_and_rank([weak, strong], _profile(), Settings())

    assert [r.investor_firm for r in rows] == ["Strong Ventures", "Weak Ventures"]
    assert underfilled is True  # only 2 rows, well under the 30 threshold


def test_founder_context_only_breaks_ties_never_reorders_across_scores():
    strong = InvestorRecord(
        firm="Strong Ventures", firm_normalized="strong", person=None, role=None,
        evidence=[_evidence(investor_firm="Strong Ventures", confidence=1.0, kind="portfolio_investment")],
    )
    weak_with_signal = InvestorRecord(
        firm="Weak Ventures", firm_normalized="weak", person=None, role=None,
        evidence=[_evidence(investor_firm="Weak Ventures", confidence=0.2, kind="other", claim="Stanford alum fund")],
    )
    profile = _profile(founder_context=["Stanford"])

    rows, _ = score_and_rank([weak_with_signal, strong], profile, Settings())

    # Signal never promotes the weak investor above the clearly stronger one.
    assert [r.investor_firm for r in rows] == ["Strong Ventures", "Weak Ventures"]


def test_founder_context_breaks_a_genuine_tie():
    tied_a = InvestorRecord(
        firm="A Ventures", firm_normalized="a", person=None, role=None,
        evidence=[_evidence(investor_firm="A Ventures", confidence=0.5, kind="other", claim="no signal here")],
    )
    tied_b = InvestorRecord(
        firm="B Ventures", firm_normalized="b", person=None, role=None,
        evidence=[_evidence(investor_firm="B Ventures", confidence=0.5, kind="other", claim="Stanford grad fund")],
    )
    profile = _profile(founder_context=["Stanford"])

    rows, _ = score_and_rank([tied_a, tied_b], profile, Settings())

    assert rows[0].investor_firm == "B Ventures"
