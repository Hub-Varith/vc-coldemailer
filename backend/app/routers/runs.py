from __future__ import annotations

import asyncio
import json
from uuid import UUID

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse

from ..auth import current_user
from ..errors import ApiError, not_found
from ..events import BUS
from ..models import Run, RunCreate, SearchPlan, User
from ..pipeline import PIPELINE
from ..store.repo import REPO

router = APIRouter(prefix="/runs", tags=["runs"])

HEARTBEAT_S = 15.0


def _get_run(run_id: UUID) -> Run:
    run = REPO.runs.get(run_id)
    if not run:
        raise not_found("run", str(run_id))
    return run


@router.post("", status_code=202)
async def start_run(payload: RunCreate, _: User = Depends(current_user)) -> dict[str, str]:
    profile_id = payload.profile_id or next(iter(REPO.profiles))
    profile = REPO.profiles.get(profile_id)
    if not profile:
        raise not_found("profile", str(profile_id))
    run = Run(profile_id=profile.id)
    await REPO.save_run(run)
    asyncio.create_task(PIPELINE.run(run, profile))
    return {"run_id": str(run.run_id), "status": "queued"}


@router.get("", response_model=list[Run])
async def list_runs(limit: int = 20, _: User = Depends(current_user)) -> list[Run]:
    return sorted(REPO.runs.values(), key=lambda r: r.started_at, reverse=True)[:limit]


@router.get("/{run_id}", response_model=Run)
async def get_run(run_id: UUID, _: User = Depends(current_user)) -> Run:
    return _get_run(run_id)


@router.get("/{run_id}/plan", response_model=SearchPlan)
async def get_plan(run_id: UUID, _: User = Depends(current_user)) -> SearchPlan:
    _get_run(run_id)
    plan = REPO.plans.get(run_id)
    if not plan:
        raise not_found("plan", str(run_id))
    return plan


@router.get("/{run_id}/events")
async def stream_events(run_id: UUID, request: Request) -> StreamingResponse:
    run = _get_run(run_id)
    queue = BUS.subscribe(run_id)
    replay = BUS.history(run_id)

    async def event_stream():
        try:
            for event in replay:
                yield f"event: {event.type}\ndata: {event.model_dump_json()}\n\n"
            if run.status in ("complete", "failed", "cancelled"):
                yield f"event: stream_end\ndata: {json.dumps({'run_id': str(run_id)})}\n\n"
                return
            while True:
                if await request.is_disconnected():
                    break
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=HEARTBEAT_S)
                except asyncio.TimeoutError:
                    yield ": heartbeat\n\n"
                    continue
                if event is None:
                    yield f"event: stream_end\ndata: {json.dumps({'run_id': str(run_id)})}\n\n"
                    break
                yield f"event: {event.type}\ndata: {event.model_dump_json()}\n\n"
        finally:
            BUS.unsubscribe(run_id, queue)

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no", "Connection": "keep-alive"},
    )


@router.post("/{run_id}/cancel", response_model=Run)
async def cancel_run(run_id: UUID, _: User = Depends(current_user)) -> Run:
    run = _get_run(run_id)
    if run.status in ("complete", "failed", "cancelled"):
        raise ApiError(409, "run_not_cancellable", f"Run is already {run.status}.")
    REPO.cancelled_runs.add(run_id)
    return run


@router.post("/{run_id}/reverify", response_model=Run)
async def reverify(run_id: UUID, _: User = Depends(current_user)) -> Run:
    run = _get_run(run_id)
    rows = REPO.rows_for_run(run_id)
    if not rows:
        raise ApiError(409, "no_targets", "This run has no targets to re-verify.")
    await PIPELINE.reverify(run, rows)
    return run


@router.delete("/{run_id}", status_code=204)
async def delete_run(run_id: UUID, _: User = Depends(current_user)) -> None:
    _get_run(run_id)
    REPO.delete_run(run_id)
