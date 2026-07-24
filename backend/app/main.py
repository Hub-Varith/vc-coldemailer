"""FastAPI app: HTTP surface for the investor targeting pipeline.

Routes are intentionally thin -- they validate input, read/write the
RunStore, and kick off app.pipeline.run_pipeline as a background task.
All real logic lives in the stage modules (planner, executor, extractor,
verifier, scorer) and in pipeline.py, which orchestrates them.
"""

import logging
from contextlib import asynccontextmanager
from uuid import UUID, uuid4

from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException
from pydantic import BaseModel

from app.config import Settings, get_settings
from app.db import get_engine
from app.models import CompanyProfile, ProfileCreate, RunStatus, SearchPlan, TargetList
from app.models_db.base import Base
from app.pipeline import run_pipeline, run_reverify
from app.store import RunStore, get_store

logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def lifespan(app: FastAPI):
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield


app = FastAPI(title="Investor Targeting Platform API", lifespan=lifespan)


class StartRunRequest(BaseModel):
    profile_id: UUID


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/profiles", response_model=CompanyProfile)
def create_profile(payload: ProfileCreate, store: RunStore = Depends(get_store)) -> CompanyProfile:
    profile = CompanyProfile(id=uuid4(), **payload.model_dump())
    store.save_profile(profile)
    return profile


@app.post("/runs")
def start_run(
    payload: StartRunRequest,
    background_tasks: BackgroundTasks,
    store: RunStore = Depends(get_store),
    settings: Settings = Depends(get_settings),
) -> dict[str, UUID]:
    profile = store.get_profile(payload.profile_id)
    if profile is None:
        raise HTTPException(status_code=404, detail="profile not found")

    run_id = uuid4()
    store.create_run(run_id, payload.profile_id)
    background_tasks.add_task(run_pipeline, run_id, profile, settings, store)
    return {"run_id": run_id}


@app.get("/runs/{run_id}", response_model=RunStatus)
def get_run(run_id: UUID, store: RunStore = Depends(get_store)) -> RunStatus:
    run = store.get_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="run not found")
    return run


@app.get("/runs/{run_id}/targets", response_model=TargetList)
def get_targets(run_id: UUID, store: RunStore = Depends(get_store)) -> TargetList:
    target_list = store.get_target_list(run_id)
    if target_list is None:
        raise HTTPException(status_code=404, detail="targets not ready for this run")
    return target_list


@app.get("/runs/{run_id}/plan", response_model=SearchPlan)
def get_plan(run_id: UUID, store: RunStore = Depends(get_store)) -> SearchPlan:
    """Debug/demo endpoint -- shows the query fan-out so the concurrency
    story is visible to a viewer, not just the final ranked list."""
    plan = store.get_plan(run_id)
    if plan is None:
        raise HTTPException(status_code=404, detail="plan not ready for this run")
    return plan


@app.post("/runs/{run_id}/reverify")
def reverify_run(
    run_id: UUID,
    background_tasks: BackgroundTasks,
    store: RunStore = Depends(get_store),
    settings: Settings = Depends(get_settings),
) -> dict[str, UUID]:
    if store.get_run(run_id) is None:
        raise HTTPException(status_code=404, detail="run not found")
    background_tasks.add_task(run_reverify, run_id, settings, store)
    return {"run_id": run_id}
