"""M5: confirms the orchestrator drives run state through every stage in
order, writes a TargetList on success, and turns a mid-pipeline exception
into a "failed" run state instead of raising."""

from datetime import date
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

import app.pipeline as pipeline
from app.config import Settings
from app.models import (
    CompanyProfile, EvidenceRecord, InvestorRecord, OctenQuery, RetrievalBundle,
    RetrievalStats, SearchIntent, SearchPlan, TargetRow,
)
from app.store import RunStore


def _profile() -> CompanyProfile:
    return CompanyProfile(
        id=uuid4(), company_name="Test Co", one_liner="x", sector="medtech",
        product_description="x", stage="seed", geography="US",
    )


def _plan(profile_id) -> SearchPlan:
    intent = SearchIntent(kind="thesis_signal", rationale="r", queries=["q1", "q2", "q3", "q4", "q5"])
    return SearchPlan(profile_id=profile_id, intents=[intent])


def _bundle(profile_id, failed=0, total=5) -> RetrievalBundle:
    stats = RetrievalStats(query_count=total, result_count=1, failed_query_count=failed, wall_time_s=0.1)
    return RetrievalBundle(profile_id=profile_id, results=[], stats=stats)


def _investor() -> InvestorRecord:
    evidence = EvidenceRecord(
        investor_firm="Acme", kind="portfolio_investment", claim="c",
        event_date=date.today(), source_url="https://x.com", confidence=0.9, stale=False,
    )
    return InvestorRecord(firm="Acme", firm_normalized="acme", person=None, role=None, evidence=[evidence])


def _row() -> TargetRow:
    investor = _investor()
    return TargetRow(
        investor_firm=investor.firm, score=1.0, evidence=investor.evidence, lead_evidence=investor.evidence[0],
    )


@pytest.fixture()
def store() -> RunStore:
    return RunStore()


async def test_run_pipeline_happy_path_produces_target_list(store, monkeypatch):
    profile = _profile()
    run_id = uuid4()
    store.create_run(run_id, profile.id)

    monkeypatch.setattr(pipeline, "build_search_plan", AsyncMock(return_value=_plan(profile.id)))
    monkeypatch.setattr(pipeline, "execute", AsyncMock(return_value=_bundle(profile.id)))
    monkeypatch.setattr(pipeline, "extract", AsyncMock(return_value=[_investor()]))
    monkeypatch.setattr(pipeline, "verify", AsyncMock(side_effect=lambda investors, *_: investors))
    monkeypatch.setattr(pipeline, "score_and_rank", lambda investors, profile, settings: ([_row()], True))
    monkeypatch.setattr(pipeline, "OctenClient", lambda settings: AsyncMock(aclose=AsyncMock()))

    await pipeline.run_pipeline(run_id, profile, Settings(), store)

    run = store.get_run(run_id)
    assert run.status == "complete"
    assert run.stage == "complete"
    target_list = store.get_target_list(run_id)
    assert target_list is not None
    assert len(target_list.rows) == 1
    assert "list_underfilled: fewer than 30 investors qualified -- profile may be too vague" in target_list.warnings


async def test_run_pipeline_marks_run_degraded_on_high_failure_rate(store, monkeypatch):
    profile = _profile()
    run_id = uuid4()
    store.create_run(run_id, profile.id)

    monkeypatch.setattr(pipeline, "build_search_plan", AsyncMock(return_value=_plan(profile.id)))
    monkeypatch.setattr(pipeline, "execute", AsyncMock(return_value=_bundle(profile.id, failed=4, total=5)))
    monkeypatch.setattr(pipeline, "extract", AsyncMock(return_value=[_investor()]))
    monkeypatch.setattr(pipeline, "verify", AsyncMock(side_effect=lambda investors, *_: investors))
    monkeypatch.setattr(pipeline, "score_and_rank", lambda investors, profile, settings: ([_row()], True))
    monkeypatch.setattr(pipeline, "OctenClient", lambda settings: AsyncMock(aclose=AsyncMock()))

    await pipeline.run_pipeline(run_id, profile, Settings(), store)

    target_list = store.get_target_list(run_id)
    assert "run degraded: over 30% of retrieval queries failed" in target_list.warnings


async def test_run_pipeline_failure_sets_failed_state_and_never_raises(store, monkeypatch):
    profile = _profile()
    run_id = uuid4()
    store.create_run(run_id, profile.id)

    monkeypatch.setattr(pipeline, "build_search_plan", AsyncMock(side_effect=RuntimeError("openai down")))

    await pipeline.run_pipeline(run_id, profile, Settings(), store)  # must not raise

    run = store.get_run(run_id)
    assert run.status == "failed"
    assert run.stage == "failed"
    assert run.error == "openai down"


async def test_cancel_requested_stops_the_pipeline_between_stages(store, monkeypatch):
    profile = _profile()
    run_id = uuid4()
    store.create_run(run_id, profile.id)
    store.request_cancel(run_id)

    plan_mock = AsyncMock(return_value=_plan(profile.id))
    monkeypatch.setattr(pipeline, "build_search_plan", plan_mock)
    execute_mock = AsyncMock(return_value=_bundle(profile.id))
    monkeypatch.setattr(pipeline, "execute", execute_mock)

    await pipeline.run_pipeline(run_id, profile, Settings(), store)

    run = store.get_run(run_id)
    assert run.stage == "cancelled"
    assert run.status == "cancelled"
    execute_mock.assert_not_awaited()  # never reached stage 3 -- cancel caught right after planning


async def test_reverify_preserves_target_id_status_and_notes(store, monkeypatch):
    from datetime import datetime, timezone

    from app.models import TargetList

    profile = _profile()
    store.save_profile(profile)
    run_id = uuid4()
    store.create_run(run_id, profile.id)

    original_row = _row()
    original_row = original_row.model_copy(update={"status": "approved", "notes": "great fit"})
    target_list = TargetList(
        run_id=run_id, profile_id=profile.id, generated_at=datetime.now(timezone.utc),
        rows=[original_row], retrieval_stats=_bundle(profile.id).stats,
    )
    store.save_target_list(run_id, target_list)

    monkeypatch.setattr(pipeline, "verify", AsyncMock(side_effect=lambda investors, *_: investors))
    monkeypatch.setattr(pipeline, "score_and_rank", lambda investors, profile, settings: ([_row()], True))
    monkeypatch.setattr(pipeline, "OctenClient", lambda settings: AsyncMock(aclose=AsyncMock()))

    await pipeline.run_reverify(run_id, Settings(), store)

    updated_list = store.get_target_list(run_id)
    assert updated_list.rows[0].target_id == original_row.target_id
    assert updated_list.rows[0].status == "approved"
    assert updated_list.rows[0].notes == "great fit"
