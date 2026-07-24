"""The frozen TargetList contract (BACKEND_SPEC §7, M6).

`tests/fixtures/target_list.json` is the file the Composio module develops against
without running the pipeline. These tests assert the guarantees the backend makes to it.
"""

from app.models import TargetList

from .conftest import load_fixture


def _target_list() -> TargetList:
    return TargetList.model_validate(load_fixture("target_list.json"))


def test_fixture_parses_as_the_published_contract():
    target_list = _target_list()
    assert target_list.rows, "the fixture is non-empty so the other owner can build against it"
    assert target_list.retrieval_stats.queries_issued > 0


def test_lead_evidence_is_present_fresh_and_attributable():
    for row in _target_list().rows:
        assert row.lead_evidence.source_url, "lead evidence always cites a source"
        assert row.lead_evidence.stale is False, "a stale fact never opens an email"
        assert row.lead_evidence.effective_date is not None


def test_every_record_is_dated_and_attributable():
    for row in _target_list().rows:
        for record in row.evidence:
            assert record.source_url
            assert record.effective_date is not None


def test_rows_are_sorted_and_capped():
    rows = _target_list().rows
    assert [r.score for r in rows] == sorted((r.score for r in rows), reverse=True)
    assert len(rows) <= 80


def test_empty_evidence_never_appears():
    assert all(row.evidence for row in _target_list().rows), "if we can't prove it, we don't ship the row"
