"""Demo control surface: profile edit, reset, and the choreographed live search."""

from __future__ import annotations

import asyncio
from uuid import UUID

from fastapi import APIRouter
from pydantic import BaseModel

from ..errors import not_found
from ..models import CompanyProfile, CompanyProfilePatch, Run, utcnow
from ..pipeline import PIPELINE
from ..seed import DEMO_PROFILE, seed
from ..store.repo import REPO

router = APIRouter(prefix="/demo", tags=["demo"])


class SearchChoreography(BaseModel):
    run_id: UUID
    sources_searched: int
    candidates_found: int
    stale_rejected: int
    investors_verified: int
    evidence_coverage: float
    queries_issued: int
    wall_time_ms: int
    top_target_id: UUID | None


def _profile() -> CompanyProfile:
    profile = REPO.profiles.get(DEMO_PROFILE.id) or next(iter(REPO.profiles.values()), None)
    if not profile:
        raise not_found("profile", "current")
    return profile


@router.get("/profile", response_model=CompanyProfile)
async def get_profile() -> CompanyProfile:
    return _profile()


@router.put("/profile", response_model=CompanyProfile)
async def update_profile(patch: CompanyProfilePatch) -> CompanyProfile:
    profile = _profile()
    for field, value in patch.model_dump(exclude_none=True).items():
        setattr(profile, field, value)
    profile.updated_at = utcnow()
    return profile


@router.post("/search", response_model=SearchChoreography)
async def run_search() -> SearchChoreography:
    """Runs the real pipeline and returns the counters the activity tray animates to."""
    profile = _profile()
    run = Run(profile_id=profile.id)
    await REPO.save_run(run)
    await PIPELINE.run(run, profile)

    rows = REPO.rows_for_run(run.run_id)
    evidence_backed = sum(1 for row in rows if row.evidence)
    return SearchChoreography(
        run_id=run.run_id,
        sources_searched=run.sources_searched,
        candidates_found=len(rows) + run.rejected_count,
        stale_rejected=run.rejected_count,
        investors_verified=len(rows),
        evidence_coverage=round(evidence_backed / len(rows), 4) if rows else 0.0,
        queries_issued=run.retrieval_stats.queries_issued,
        wall_time_ms=run.retrieval_stats.wall_time_ms,
        top_target_id=rows[0].target_id if rows else None,
    )


@router.post("/reset", response_model=SearchChoreography)
async def reset_demo() -> SearchChoreography:
    """Clears every mutation and rebuilds the opening state in one call."""
    REPO.users.clear()
    REPO.sessions.clear()
    REPO.profiles.clear()
    REPO.runs.clear()
    REPO.plans.clear()
    REPO.targets.clear()
    REPO.targets_by_run.clear()
    REPO.drafts.clear()
    REPO.drafts_by_target.clear()
    REPO.sends.clear()
    REPO.sends_by_idempotency.clear()
    REPO.sequences.clear()
    REPO.replies.clear()
    REPO.cancelled_runs.clear()
    REPO.warnings.clear()
    seed()
    await asyncio.sleep(0)
    return await run_search()
