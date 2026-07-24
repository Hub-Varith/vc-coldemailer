"""M6: freezes the Composio handoff contract. If this test breaks, the
TargetList schema changed -- update tests/fixtures/target_list_example.json
and tell the Composio module owner, since they develop against this file
without running the pipeline (BACKEND_SPEC.md Sec 7 and Sec 11 M6)."""

import json
from pathlib import Path

from app.models import TargetList

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "target_list_example.json"


def test_fixture_parses_as_target_list():
    raw = json.loads(FIXTURE_PATH.read_text())
    target_list = TargetList.model_validate(raw)
    assert len(target_list.rows) == 1


def test_every_row_has_non_stale_lead_evidence_with_a_source():
    target_list = TargetList.model_validate(json.loads(FIXTURE_PATH.read_text()))
    for row in target_list.rows:
        assert row.lead_evidence.stale is False
        assert row.lead_evidence.source_url
        assert row.evidence  # "no evidence, no listing" -- never empty


def test_rows_sorted_by_score_descending():
    target_list = TargetList.model_validate(json.loads(FIXTURE_PATH.read_text()))
    scores = [row.score for row in target_list.rows]
    assert scores == sorted(scores, reverse=True)
