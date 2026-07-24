"""Orchestrates the six pipeline stages end to end: plan -> retrieve ->
extract -> verify -> score -> TargetList. Runs as a background task kicked
off by POST /api/v1/runs; progress is visible via GET /api/v1/runs/{run_id}
and streamed live over GET /api/v1/runs/{run_id}/events, because every
stage writes its state to the shared RunStore as it goes.

The pipeline always terminates (BACKEND_SPEC.md Sec 9): any exception is
caught, logged, and turned into a "failed" run state rather than left to
crash the background task silently. Cancellation (POST .../cancel) is
cooperative -- checked between stages, not a hard task-kill -- so an
in-flight OpenAI/Octen call always finishes cleanly before a run stops.
"""

import logging
from datetime import datetime, timezone
from uuid import UUID

from app.config import Settings
from app.executor import execute
from app.extractor import _normalize_firm_name, extract
from app.models import CompanyProfile, InvestorRecord, RetrievalStats, TargetList, TargetRow
from app.octen_client import OctenClient
from app.planner import build_search_plan
from app.scorer import score_and_rank
from app.store import RunStore
from app.verifier import verify

logger = logging.getLogger(__name__)

_DEGRADED_FAILURE_RATE = 0.3


# --- public API ---


async def run_pipeline(run_id: UUID, profile: CompanyProfile, settings: Settings, store: RunStore) -> None:
    try:
        await _run_stages(run_id, profile, settings, store)
    except Exception as exc:
        logger.exception("pipeline failed for run=%s", run_id)
        store.update_run_stage(run_id, "failed", error=str(exc))


async def run_reverify(run_id: UUID, settings: Settings, store: RunStore) -> None:
    """POST /api/v1/runs/{run_id}/reverify -- re-run stages 5-6 (verify +
    score) against the evidence already extracted for this run. Cheaper
    than a full pipeline run: no new planning or retrieval fan-out."""
    try:
        await _reverify_stages(run_id, settings, store)
    except Exception as exc:
        logger.exception("reverify failed for run=%s", run_id)
        store.update_run_stage(run_id, "failed", error=str(exc))


async def _reverify_stages(run_id: UUID, settings: Settings, store: RunStore) -> None:
    target_list = store.get_target_list(run_id)
    if target_list is None:
        raise ValueError(f"no target list for run {run_id} -- run the full pipeline first")
    profile = store.get_profile(target_list.profile_id)
    if profile is None:
        raise ValueError(f"no profile found for run {run_id}")

    investors = [
        InvestorRecord(
            firm=row.investor_firm,
            firm_normalized=_normalize_firm_name(row.investor_firm),
            person=row.investor_person,
            role=row.role,
            evidence=row.evidence,
        )
        for row in target_list.rows
    ]

    octen_client = OctenClient(settings)
    try:
        store.update_run_stage(run_id, "verifying", retrieval_stats=target_list.retrieval_stats)
        investors = await verify(investors, settings, octen_client)
    finally:
        await octen_client.aclose()

    if _bail_if_cancelled(run_id, store):
        return

    store.update_run_stage(run_id, "scoring", retrieval_stats=target_list.retrieval_stats)
    rows, list_underfilled = score_and_rank(investors, profile, settings)
    rows = _preserve_target_state(rows, target_list.rows)
    warnings = _build_warnings(target_list.retrieval_stats, list_underfilled)
    store.update_run_progress(run_id, investors=len(rows))

    updated = target_list.model_copy(
        update={"rows": rows, "warnings": warnings, "generated_at": datetime.now(timezone.utc)}
    )
    store.save_target_list(run_id, updated)
    store.set_warnings(run_id, warnings)
    store.update_run_stage(run_id, "complete", retrieval_stats=target_list.retrieval_stats)


# --- private internals ---


async def _run_stages(run_id: UUID, profile: CompanyProfile, settings: Settings, store: RunStore) -> None:
    store.update_run_stage(run_id, "planning")
    plan = await build_search_plan(profile)
    store.save_plan(run_id, plan)
    store.update_run_progress(run_id, queries_total=plan.query_count)

    if _bail_if_cancelled(run_id, store):
        return

    octen_client = OctenClient(settings)
    try:
        store.update_run_stage(run_id, "retrieving")
        bundle = await execute(plan, settings, octen_client)
        store.update_run_progress(run_id, queries_done=bundle.stats.query_count, results=bundle.stats.result_count)

        if _bail_if_cancelled(run_id, store):
            return

        store.update_run_stage(run_id, "extracting", retrieval_stats=bundle.stats)
        investors = await extract(bundle, settings)
        store.update_run_progress(run_id, evidence=sum(len(i.evidence) for i in investors))

        if _bail_if_cancelled(run_id, store):
            return

        store.update_run_stage(run_id, "verifying", retrieval_stats=bundle.stats)
        investors = await verify(investors, settings, octen_client)
    finally:
        await octen_client.aclose()

    if _bail_if_cancelled(run_id, store):
        return

    store.update_run_stage(run_id, "scoring", retrieval_stats=bundle.stats)
    rows, list_underfilled = score_and_rank(investors, profile, settings)
    store.update_run_progress(run_id, investors=len(rows))

    warnings = _build_warnings(bundle.stats, list_underfilled)
    target_list = TargetList(
        run_id=run_id,
        profile_id=profile.id,
        generated_at=datetime.now(timezone.utc),
        rows=rows,
        retrieval_stats=bundle.stats,
        warnings=warnings,
    )
    store.save_target_list(run_id, target_list)
    store.set_warnings(run_id, warnings)
    store.update_run_stage(run_id, "complete", retrieval_stats=bundle.stats)


def _bail_if_cancelled(run_id: UUID, store: RunStore) -> bool:
    if not store.is_cancel_requested(run_id):
        return False
    store.update_run_stage(run_id, "cancelled")
    return True


# --- static helpers ---


def _preserve_target_state(new_rows: list[TargetRow], old_rows: list[TargetRow]) -> list[TargetRow]:
    """Reverify rescores from scratch, which would otherwise mint a new
    target_id per row -- carry over the old (target_id, status, notes) for
    any investor that's still on the list, so a frontend that already
    rendered a row keeps a stable reference to it."""
    old_by_investor = {(row.investor_firm, row.investor_person): row for row in old_rows}
    preserved = []
    for row in new_rows:
        old = old_by_investor.get((row.investor_firm, row.investor_person))
        if old is not None:
            row = row.model_copy(update={"target_id": old.target_id, "status": old.status, "notes": old.notes})
        preserved.append(row)
    return preserved


def _build_warnings(stats: RetrievalStats, list_underfilled: bool) -> list[str]:
    warnings = []
    if stats.query_count and stats.failed_query_count / stats.query_count > _DEGRADED_FAILURE_RATE:
        warnings.append("run degraded: over 30% of retrieval queries failed")
    if list_underfilled:
        warnings.append("list_underfilled: fewer than 30 investors qualified -- profile may be too vague")
    return warnings
