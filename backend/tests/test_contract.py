"""Guards the backend->Composio seam (BACKEND_SPEC.md §7).

If the Octen owner changes a field in models/output.py, or the pinned fixture
drifts from the frozen shape, this fails loudly — not at the demo.
"""

from app.models.output import TargetList


def test_fixture_matches_frozen_contract(target_list: TargetList) -> None:
    # Fixture parsed cleanly via the conftest fixture -> the shape is valid.
    assert target_list.rows, "fixture must carry at least one row"


def test_lead_evidence_guarantees_hold(target_list: TargetList) -> None:
    # Guarantees the backend promises Composio (BACKEND_SPEC §7).
    for row in target_list.rows:
        assert row.lead_evidence.source_url, "lead_evidence must have a source_url"
        assert not row.lead_evidence.stale, "lead_evidence must never be stale"
        assert row.evidence, "empty evidence never appears"
