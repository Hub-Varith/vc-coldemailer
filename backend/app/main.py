"""FastAPI app: HTTP surface for the investor targeting pipeline.

Routes under /api/v1 follow the frontend contract in ../API_ENDPOINTS.md.
This module only implements the backend/pipeline owner's slice of that
contract: Company profile (Sec 3), Runs (Sec 4), Targets (Sec 5), and
System health/usage (Sec 10). Auth (Sec 1, not built by anyone yet),
Integrations (Sec 2), Drafts & approval (Sec 6), Sending & sequences
(Sec 7), Replies (Sec 8), and Export destinations (Sec 9) belong to the
Composio module (see docs/superpowers/specs/2026-07-23-composio-integration-design.md)
and are not implemented here.

Routes are intentionally thin -- they validate input, read/write the
RunStore, and kick off app.pipeline.run_pipeline/run_reverify as
background tasks. All real logic lives in the stage modules (planner,
executor, extractor, verifier, scorer) and in pipeline.py.
"""

import csv
import io
import json
import logging
from base64 import urlsafe_b64decode, urlsafe_b64encode
from contextlib import asynccontextmanager
from datetime import date
from uuid import UUID, uuid4

from fastapi import APIRouter, BackgroundTasks, Depends, FastAPI
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel
from starlette.requests import Request

from app.composio_routes import router as composio_router
from app.config import Settings, get_settings
from app.db import get_engine
from app.models import (
    ApiErrorBody, ApiErrorEnvelope, CompanyProfile, ProfileCreate, ProfileUpdate, ProfileValidation,
    RunStatus, SearchPlan, TargetRow, TargetsPage, TargetSummary, TargetUpdate,
)
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
router = APIRouter(prefix="/api/v1")

_GENERIC_SECTORS = {"tech", "software", "saas", "fintech", "medtech", "healthcare", "ai", "biotech", "consumer"}
_TERMINAL_RUN_STATUSES = {"complete", "failed", "cancelled"}


class ApiError(Exception):
    """Raised by any route to produce the error envelope API_ENDPOINTS.md's
    conventions require -- never a bare string."""

    def __init__(self, status_code: int, code: str, message: str, details: dict | None = None) -> None:
        self.status_code = status_code
        self.code = code
        self.message = message
        self.details = details or {}


@app.exception_handler(ApiError)
async def _handle_api_error(_request: Request, exc: ApiError) -> JSONResponse:
    envelope = ApiErrorEnvelope(error=ApiErrorBody(code=exc.code, message=exc.message, details=exc.details))
    return JSONResponse(status_code=exc.status_code, content=envelope.model_dump(mode="json"))


class StartRunRequest(BaseModel):
    profile_id: UUID


# --- system (API_ENDPOINTS.md Sec 10) ---


@app.get("/api/health")
@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/usage")
def get_usage(store: RunStore = Depends(get_store)) -> dict:
    """Best-effort: only reports numbers we actually track (see
    BACKEND_SPEC.md Sec 6 -- token spend isn't captured yet, so it's
    reported as null rather than fabricated)."""
    runs = store.list_runs()
    return {
        "runs_used": len(runs),
        "queries_consumed": sum(r.progress.queries_done for r in runs),
        "token_spend_usd": None,
    }


# --- profiles (API_ENDPOINTS.md Sec 3) ---


@router.post("/profiles", response_model=CompanyProfile)
def create_profile(payload: ProfileCreate, store: RunStore = Depends(get_store)) -> CompanyProfile:
    profile = CompanyProfile(id=uuid4(), **payload.model_dump())
    store.save_profile(profile)
    return profile


@router.get("/profiles", response_model=list[CompanyProfile])
def list_profiles(store: RunStore = Depends(get_store)) -> list[CompanyProfile]:
    return store.list_profiles()


@router.get("/profiles/{profile_id}", response_model=CompanyProfile)
def get_profile(profile_id: UUID, store: RunStore = Depends(get_store)) -> CompanyProfile:
    profile = store.get_profile(profile_id)
    if profile is None:
        raise ApiError(404, "profile_not_found", "profile not found")
    return profile


@router.patch("/profiles/{profile_id}", response_model=CompanyProfile)
def update_profile(profile_id: UUID, payload: ProfileUpdate, store: RunStore = Depends(get_store)) -> CompanyProfile:
    updated = store.update_profile(profile_id, payload)
    if updated is None:
        raise ApiError(404, "profile_not_found", "profile not found")
    return updated


@router.delete("/profiles/{profile_id}", status_code=204)
def delete_profile(profile_id: UUID, store: RunStore = Depends(get_store)) -> None:
    if not store.delete_profile(profile_id):
        raise ApiError(404, "profile_not_found", "profile not found")


@router.post("/profiles/{profile_id}/validate", response_model=ProfileValidation)
def validate_profile(profile_id: UUID, store: RunStore = Depends(get_store)) -> ProfileValidation:
    profile = store.get_profile(profile_id)
    if profile is None:
        raise ApiError(404, "profile_not_found", "profile not found")
    return _validate_profile(profile)


# --- runs (API_ENDPOINTS.md Sec 4) ---


@router.post("/runs", status_code=202)
def start_run(
    payload: StartRunRequest,
    background_tasks: BackgroundTasks,
    store: RunStore = Depends(get_store),
    settings: Settings = Depends(get_settings),
) -> dict:
    profile = store.get_profile(payload.profile_id)
    if profile is None:
        raise ApiError(404, "profile_not_found", "profile not found")

    run_id = uuid4()
    run = store.create_run(run_id, payload.profile_id)
    background_tasks.add_task(run_pipeline, run_id, profile, settings, store)
    return {"run_id": run_id, "status": run.status}


@router.get("/runs")
def list_runs(profile_id: UUID | None = None, store: RunStore = Depends(get_store)) -> dict:
    return {"runs": store.list_runs(profile_id)}


@router.get("/runs/{run_id}", response_model=RunStatus)
def get_run(run_id: UUID, store: RunStore = Depends(get_store)) -> RunStatus:
    run = store.get_run(run_id)
    if run is None:
        raise ApiError(404, "run_not_found", "run not found")
    return run


@router.get("/runs/{run_id}/events")
async def stream_run_events(run_id: UUID, store: RunStore = Depends(get_store)) -> StreamingResponse:
    """SSE stream of stage_changed / query_batch_done / investor_found /
    run_complete events. Single-subscriber per run (an asyncio.Queue, not
    a broadcast fan-out) -- fine for one frontend tab watching a run,
    which is the only case this needs to support right now."""
    run = store.get_run(run_id)
    if run is None:
        raise ApiError(404, "run_not_found", "run not found")

    return StreamingResponse(_run_event_stream(run_id, run, store), media_type="text/event-stream")


@router.post("/runs/{run_id}/cancel", response_model=RunStatus)
def cancel_run(run_id: UUID, store: RunStore = Depends(get_store)) -> RunStatus:
    run = store.get_run(run_id)
    if run is None:
        raise ApiError(404, "run_not_found", "run not found")
    store.request_cancel(run_id)
    return run


@router.post("/runs/{run_id}/reverify", status_code=202)
def reverify_run(
    run_id: UUID,
    background_tasks: BackgroundTasks,
    store: RunStore = Depends(get_store),
    settings: Settings = Depends(get_settings),
) -> dict:
    run = store.get_run(run_id)
    if run is None:
        raise ApiError(404, "run_not_found", "run not found")
    background_tasks.add_task(run_reverify, run_id, settings, store)
    return {"run_id": run_id, "status": run.status}


@router.delete("/runs/{run_id}", status_code=204)
def delete_run(run_id: UUID, store: RunStore = Depends(get_store)) -> None:
    if not store.delete_run(run_id):
        raise ApiError(404, "run_not_found", "run not found")


@router.get("/runs/{run_id}/plan", response_model=SearchPlan)
def get_plan(run_id: UUID, store: RunStore = Depends(get_store)) -> SearchPlan:
    """Debug/demo endpoint -- shows the query fan-out so the concurrency
    story is visible to a viewer, not just the final ranked list."""
    plan = store.get_plan(run_id)
    if plan is None:
        raise ApiError(404, "plan_not_ready", "plan not ready for this run")
    return plan


# --- targets (API_ENDPOINTS.md Sec 5) ---


@router.get("/runs/{run_id}/targets", response_model=TargetsPage)
def list_targets(
    run_id: UUID,
    limit: int = 50,
    cursor: str | None = None,
    status: str | None = None,
    min_score: float | None = None,
    has_email: bool | None = None,
    stale: bool | None = None,
    sort: str = "score",
    store: RunStore = Depends(get_store),
) -> TargetsPage:
    target_list = store.get_target_list(run_id)
    if target_list is None:
        raise ApiError(404, "targets_not_ready", "targets not ready for this run")

    rows = _filter_targets(target_list.rows, status, min_score, has_email, stale)
    rows = _sort_targets(rows, sort)

    offset = _decode_cursor(cursor)
    page = rows[offset : offset + limit]
    next_cursor = _encode_cursor(offset + limit) if offset + limit < len(rows) else None
    list_underfilled = target_list.rows[0].list_underfilled if target_list.rows else False

    return TargetsPage(
        rows=[TargetSummary.from_row(r) for r in page], next_cursor=next_cursor,
        list_underfilled=list_underfilled, total=len(rows),
    )


@router.get("/targets/{target_id}", response_model=TargetRow)
def get_target(target_id: UUID, store: RunStore = Depends(get_store)) -> TargetRow:
    found = store.get_target_row(target_id)
    if found is None:
        raise ApiError(404, "target_not_found", "target not found")
    return found[1]


@router.patch("/targets/{target_id}", response_model=TargetRow)
def update_target(target_id: UUID, payload: TargetUpdate, store: RunStore = Depends(get_store)) -> TargetRow:
    updated = store.update_target_row(target_id, **payload.model_dump(exclude_unset=True))
    if updated is None:
        raise ApiError(404, "target_not_found", "target not found")
    return updated


@router.post("/targets/{target_id}/dismiss", response_model=TargetRow)
def dismiss_target(target_id: UUID, store: RunStore = Depends(get_store)) -> TargetRow:
    updated = store.update_target_row(target_id, status="dismissed")
    if updated is None:
        raise ApiError(404, "target_not_found", "target not found")
    return updated


@router.get("/runs/{run_id}/targets/export")
def export_targets(run_id: UUID, store: RunStore = Depends(get_store)) -> StreamingResponse:
    target_list = store.get_target_list(run_id)
    if target_list is None:
        raise ApiError(404, "targets_not_ready", "targets not ready for this run")

    csv_text = _rows_to_csv(target_list.rows)
    headers = {"Content-Disposition": f'attachment; filename="run-{run_id}-targets.csv"'}
    return StreamingResponse(iter([csv_text]), media_type="text/csv", headers=headers)


app.include_router(router)
app.include_router(composio_router)


# --- static helpers ---


async def _run_event_stream(run_id: UUID, run: RunStatus, store: RunStore):
    if run.status in _TERMINAL_RUN_STATUSES:
        yield _format_sse("run_complete", run.model_dump(mode="json"))
        return

    queue = store.subscribe_events(run_id)
    while True:
        item = await queue.get()
        if item is None:  # terminal sentinel, see RunStore.publish_event
            break
        yield _format_sse(item["event"], item["data"])


def _format_sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, default=str)}\n\n"


def _validate_profile(profile: CompanyProfile) -> ProfileValidation:
    warnings: list[str] = []
    suggestions: list[str] = []
    if profile.sector.strip().lower() in _GENERIC_SECTORS:
        warnings.append("sector_too_broad")
        suggestions.append("Name the specific product category, not just a broad sector label")
    if not profile.stage.strip():
        warnings.append("no_stage_specified")
        suggestions.append("Specify a funding stage (e.g. 'seed', 'series-a')")
    if len(profile.product_description.split()) < 6:
        warnings.append("product_description_too_thin")
        suggestions.append("Describe the product in enough detail to distinguish it from competitors")
    return ProfileValidation(ok=not warnings, warnings=warnings, suggestions=suggestions)


def _filter_targets(
    rows: list[TargetRow], status: str | None, min_score: float | None, has_email: bool | None, stale: bool | None
) -> list[TargetRow]:
    if status is not None:
        rows = [r for r in rows if r.status == status]
    if min_score is not None:
        rows = [r for r in rows if r.score >= min_score]
    if has_email is not None:
        rows = [r for r in rows if (r.contact_email is not None) == has_email]
    if stale is not None:
        rows = [r for r in rows if any(e.stale for e in r.evidence) == stale]
    return rows


def _sort_targets(rows: list[TargetRow], sort: str) -> list[TargetRow]:
    if sort == "firm":
        return sorted(rows, key=lambda r: r.investor_firm.lower())
    if sort == "recency":
        return sorted(
            rows, key=lambda r: r.lead_evidence.event_date or r.lead_evidence.source_published_at or date.min,
            reverse=True,
        )
    return rows  # "score" -- already sorted by the scorer


def _encode_cursor(offset: int) -> str:
    return urlsafe_b64encode(str(offset).encode()).decode()


def _decode_cursor(cursor: str | None) -> int:
    if not cursor:
        return 0
    try:
        return max(0, int(urlsafe_b64decode(cursor.encode()).decode()))
    except (ValueError, UnicodeDecodeError):
        return 0


def _rows_to_csv(rows: list[TargetRow]) -> str:
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow([
        "investor_firm", "investor_person", "role", "score", "status",
        "contact_email", "firm_domain", "lead_evidence_claim", "lead_evidence_source_url",
    ])
    for row in rows:
        writer.writerow([
            row.investor_firm, row.investor_person or "", row.role or "", row.score, row.status,
            row.contact_email or "", row.firm_domain or "", row.lead_evidence.claim, row.lead_evidence.source_url,
        ])
    return buffer.getvalue()
