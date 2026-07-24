"""In-memory persistence for profiles and runs.

Good enough for v1 (BACKEND_SPEC.md Sec 2 allows this for local dev/demo
scope) -- state is lost on process restart. Swap for Postgres/SQLite behind
this same interface if runs need to survive a restart.
"""

import logging
from functools import lru_cache
from uuid import UUID

from app.models import CompanyProfile, RetrievalStats, RunStatus, SearchPlan, TargetList

logger = logging.getLogger(__name__)


class RunStore:
    def __init__(self) -> None:
        self._profiles: dict[UUID, CompanyProfile] = {}
        self._runs: dict[UUID, RunStatus] = {}
        self._plans: dict[UUID, SearchPlan] = {}
        self._target_lists: dict[UUID, TargetList] = {}

    # --- public API ---

    def save_profile(self, profile: CompanyProfile) -> None:
        self._profiles[profile.id] = profile

    def get_profile(self, profile_id: UUID) -> CompanyProfile | None:
        return self._profiles.get(profile_id)

    def create_run(self, run_id: UUID, profile_id: UUID) -> RunStatus:
        run = RunStatus(run_id=run_id, profile_id=profile_id, state="pending")
        self._runs[run_id] = run
        return run

    def update_run_state(
        self, run_id: UUID, state: str, error: str | None = None, retrieval_stats: RetrievalStats | None = None
    ) -> None:
        run = self._runs[run_id]
        updated = run.model_copy(update={"state": state, "error": error, "retrieval_stats": retrieval_stats or run.retrieval_stats})
        self._runs[run_id] = updated
        logger.info("run=%s state=%s", run_id, state)

    def get_run(self, run_id: UUID) -> RunStatus | None:
        return self._runs.get(run_id)

    def save_plan(self, run_id: UUID, plan: SearchPlan) -> None:
        self._plans[run_id] = plan

    def get_plan(self, run_id: UUID) -> SearchPlan | None:
        return self._plans.get(run_id)

    def save_target_list(self, run_id: UUID, target_list: TargetList) -> None:
        self._target_lists[run_id] = target_list

    def get_target_list(self, run_id: UUID) -> TargetList | None:
        return self._target_lists.get(run_id)


@lru_cache
def get_store() -> RunStore:
    """One store per process -- routes and the pipeline share it via this
    singleton so state written during a background run is visible to the
    next GET request."""
    return RunStore()
