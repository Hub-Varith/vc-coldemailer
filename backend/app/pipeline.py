"""Orchestrates the six pipeline stages end to end: plan -> retrieve ->
extract -> verify -> score -> TargetList. Runs as a background task kicked
off by POST /runs; progress is visible via GET /runs/{run_id} because every
stage writes its state to the shared RunStore as it goes.

The pipeline always terminates (BACKEND_SPEC.md Sec 9): any exception is
caught, logged, and turned into a "failed" run state rather than left to
crash the background task silently.
"""

import logging
from datetime import datetime, timezone
from uuid import UUID

from app.config import Settings
from app.executor import execute
from app.extractor import _normalize_firm_name, extract
from app.models import CompanyProfile, InvestorRecord, TargetList
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
        store.update_run_state(run_id, "failed", error=str(exc))


async def run_reverify(run_id: UUID, settings: Settings, store: RunStore) -> None:
    """POST /runs/{run_id}/reverify -- re-run stages 5-6 (verify + score)
    against the evidence already extracted for this run. Cheaper than a
    full pipeline run: no new planning or retrieval fan-out."""
    try:
        await _reverify_stages(run_id, settings, store)
    except Exception as exc:
        logger.exception("reverify failed for run=%s", run_id)
        store.update_run_state(run_id, "failed", error=str(exc))


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
        store.update_run_state(run_id, "verifying", retrieval_stats=target_list.retrieval_stats)
        investors = await verify(investors, settings, octen_client)
    finally:
        await octen_client.aclose()

    store.update_run_state(run_id, "scoring", retrieval_stats=target_list.retrieval_stats)
    rows, list_underfilled = score_and_rank(investors, profile, settings)
    warnings = _build_warnings(target_list.retrieval_stats, list_underfilled)

    updated = target_list.model_copy(
        update={"rows": rows, "warnings": warnings, "generated_at": datetime.now(timezone.utc)}
    )
    store.save_target_list(run_id, updated)
    store.update_run_state(run_id, "done", retrieval_stats=target_list.retrieval_stats)


# --- private internals ---


async def _run_stages(run_id: UUID, profile: CompanyProfile, settings: Settings, store: RunStore) -> None:
    store.update_run_state(run_id, "planning")
    plan = await build_search_plan(profile)
    store.save_plan(run_id, plan)

    octen_client = OctenClient(settings)
    try:
        store.update_run_state(run_id, "retrieving")
        bundle = await execute(plan, settings, octen_client)
        store.update_run_state(run_id, "extracting", retrieval_stats=bundle.stats)

        investors = await extract(bundle, settings)

        store.update_run_state(run_id, "verifying", retrieval_stats=bundle.stats)
        investors = await verify(investors, settings, octen_client)
    finally:
        await octen_client.aclose()

    store.update_run_state(run_id, "scoring", retrieval_stats=bundle.stats)
    rows, list_underfilled = score_and_rank(investors, profile, settings)

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
    store.update_run_state(run_id, "done", retrieval_stats=bundle.stats)


# --- static helpers ---


def _build_warnings(stats, list_underfilled: bool) -> list[str]:
    warnings = []
    if stats.query_count and stats.failed_query_count / stats.query_count > _DEGRADED_FAILURE_RATE:
        warnings.append("run degraded: over 30% of retrieval queries failed")
    if list_underfilled:
        warnings.append("list_underfilled: fewer than 30 investors qualified -- profile may be too vague")
    return warnings
