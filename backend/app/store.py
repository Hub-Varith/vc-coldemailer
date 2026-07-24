"""In-memory persistence for profiles and runs.

Good enough for v1 (BACKEND_SPEC.md Sec 2 allows this for local dev/demo
scope) -- state is lost on process restart. Swap for Postgres/SQLite behind
this same interface if runs need to survive a restart.

Also owns the per-run SSE event queue (GET /api/v1/runs/{id}/events,
API_ENDPOINTS.md Sec 4) and the cooperative-cancellation flag checked by
pipeline.py between stages -- both are run lifecycle concerns, so they
live next to the run's status rather than in a separate module.
"""

import asyncio
import logging
from datetime import datetime, timezone
from functools import lru_cache
from uuid import UUID

from app.models import (
    CompanyProfile, ProfileUpdate, RetrievalStats, RunProgress, RunRetrievalStats, RunStage, RunStatus,
    SearchPlan, TargetList, TargetRow,
)

logger = logging.getLogger(__name__)

_TERMINAL_STAGES = {"complete", "failed", "cancelled"}
_STAGE_TO_STATUS = {
    "queued": "queued",
    "planning": "running",
    "retrieving": "running",
    "extracting": "running",
    "verifying": "running",
    "scoring": "running",
    "complete": "complete",
    "failed": "failed",
    "cancelled": "cancelled",
}


class RunStore:
    def __init__(self) -> None:
        self._profiles: dict[UUID, CompanyProfile] = {}
        self._runs: dict[UUID, RunStatus] = {}
        self._plans: dict[UUID, SearchPlan] = {}
        self._target_lists: dict[UUID, TargetList] = {}
        self._event_queues: dict[UUID, asyncio.Queue] = {}
        self._cancel_requested: set[UUID] = set()

    # --- public API: profiles ---

    def save_profile(self, profile: CompanyProfile) -> None:
        self._profiles[profile.id] = profile

    def get_profile(self, profile_id: UUID) -> CompanyProfile | None:
        return self._profiles.get(profile_id)

    def list_profiles(self) -> list[CompanyProfile]:
        return list(self._profiles.values())

    def update_profile(self, profile_id: UUID, patch: ProfileUpdate) -> CompanyProfile | None:
        profile = self._profiles.get(profile_id)
        if profile is None:
            return None
        updated = profile.model_copy(update=patch.model_dump(exclude_unset=True))
        self._profiles[profile_id] = updated
        return updated

    def delete_profile(self, profile_id: UUID) -> bool:
        return self._profiles.pop(profile_id, None) is not None

    # --- public API: runs ---

    def create_run(self, run_id: UUID, profile_id: UUID) -> RunStatus:
        run = RunStatus(
            run_id=run_id, profile_id=profile_id, status="queued", stage="queued", started_at=_now(),
        )
        self._runs[run_id] = run
        self._event_queues[run_id] = asyncio.Queue()
        return run

    def get_run(self, run_id: UUID) -> RunStatus | None:
        return self._runs.get(run_id)

    def list_runs(self, profile_id: UUID | None = None) -> list[RunStatus]:
        runs = self._runs.values()
        if profile_id is not None:
            runs = [r for r in runs if r.profile_id == profile_id]
        return sorted(runs, key=lambda r: r.started_at or _now(), reverse=True)

    def delete_run(self, run_id: UUID) -> bool:
        self._plans.pop(run_id, None)
        self._target_lists.pop(run_id, None)
        self._event_queues.pop(run_id, None)
        self._cancel_requested.discard(run_id)
        return self._runs.pop(run_id, None) is not None

    def update_run_stage(
        self,
        run_id: UUID,
        stage: RunStage,
        error: str | None = None,
        retrieval_stats: RetrievalStats | None = None,
    ) -> RunStatus:
        run = self._runs[run_id]
        api_stats = run.retrieval_stats
        if retrieval_stats is not None:
            p50_ms = round(retrieval_stats.p50_latency_ms) if retrieval_stats.p50_latency_ms is not None else None
            api_stats = RunRetrievalStats.from_internal(retrieval_stats, p50_ms)
        updated = run.model_copy(update={
            "stage": stage,
            "status": _STAGE_TO_STATUS[stage],
            "error": error,
            "retrieval_stats": api_stats,
            "completed_at": _now() if stage in _TERMINAL_STAGES else run.completed_at,
        })
        self._runs[run_id] = updated
        logger.info("run=%s stage=%s", run_id, stage)
        self.publish_event(run_id, "stage_changed", {"stage": stage, "status": updated.status})
        if stage in _TERMINAL_STAGES:
            self.publish_event(run_id, "run_complete", updated.model_dump(mode="json"), terminal=True)
        return updated

    def update_run_progress(self, run_id: UUID, **fields: int) -> None:
        run = self._runs[run_id]
        progress = run.progress.model_copy(update={k: v for k, v in fields.items() if v is not None})
        self._runs[run_id] = run.model_copy(update={"progress": progress})

    def set_warnings(self, run_id: UUID, warnings: list[str]) -> None:
        run = self._runs[run_id]
        self._runs[run_id] = run.model_copy(update={"warnings": warnings})

    def request_cancel(self, run_id: UUID) -> None:
        self._cancel_requested.add(run_id)

    def is_cancel_requested(self, run_id: UUID) -> bool:
        return run_id in self._cancel_requested

    # --- public API: run sub-resources (plan, targets) ---

    def save_plan(self, run_id: UUID, plan: SearchPlan) -> None:
        self._plans[run_id] = plan

    def get_plan(self, run_id: UUID) -> SearchPlan | None:
        return self._plans.get(run_id)

    def save_target_list(self, run_id: UUID, target_list: TargetList) -> None:
        self._target_lists[run_id] = target_list

    def get_target_list(self, run_id: UUID) -> TargetList | None:
        return self._target_lists.get(run_id)

    def get_target_row(self, target_id: UUID) -> tuple[UUID, TargetRow] | None:
        """Scans every stored TargetList for the row -- fine at hackathon
        scale (~80 rows x a handful of runs); index by target_id if this
        store ever needs to hold many runs at once."""
        for run_id, target_list in self._target_lists.items():
            for row in target_list.rows:
                if row.target_id == target_id:
                    return run_id, row
        return None

    def update_target_row(self, target_id: UUID, **fields: object) -> TargetRow | None:
        found = self.get_target_row(target_id)
        if found is None:
            return None
        run_id, row = found
        updated_row = row.model_copy(update={k: v for k, v in fields.items() if v is not None})
        target_list = self._target_lists[run_id]
        new_rows = [updated_row if r.target_id == target_id else r for r in target_list.rows]
        self._target_lists[run_id] = target_list.model_copy(update={"rows": new_rows})
        return updated_row

    # --- public API: SSE events ---

    def publish_event(self, run_id: UUID, event: str, data: dict, terminal: bool = False) -> None:
        queue = self._event_queues.get(run_id)
        if queue is None:
            return
        queue.put_nowait({"event": event, "data": data})
        if terminal:
            queue.put_nowait(None)  # sentinel: tells subscribers to stop

    def subscribe_events(self, run_id: UUID) -> asyncio.Queue:
        return self._event_queues.setdefault(run_id, asyncio.Queue())


# --- static helpers ---


def _now() -> datetime:
    return datetime.now(timezone.utc)


@lru_cache
def get_store() -> RunStore:
    """One store per process -- routes and the pipeline share it via this
    singleton so state written during a background run is visible to the
    next GET request."""
    return RunStore()
