"""Pipeline / Octen owner's routes: profiles, runs, plan, targets.

OWNER: backend/Octen. Edit freely — the other owner does not touch this file.
"""

from fastapi import APIRouter

router = APIRouter(prefix="/api/v1", tags=["runs"])


@router.post("/runs")
async def create_run() -> dict[str, str]:
    raise NotImplementedError


@router.get("/runs/{run_id}/targets")
async def get_targets(run_id: str) -> dict[str, str]:
    raise NotImplementedError
