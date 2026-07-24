from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends

from ..auth import current_user
from ..config import get_settings
from ..errors import not_found
from ..llm import LEDGER
from ..models import (
    ExportDestination,
    ExportDestinationCreate,
    ExportResult,
    PipelineCounts,
    Reply,
    Usage,
    User,
    utcnow,
)
from ..store.repo import REPO

router = APIRouter(tags=["system"])


@router.get("/health")
async def health() -> dict[str, object]:
    settings = get_settings()
    return {
        "status": "ok",
        "retrieval": "octen" if settings.octen_enabled else "local_index",
        "llm": "openai" if settings.openai_enabled else "deterministic",
        "composio": settings.composio_enabled,
        "sending_domain_verified": settings.sending_domain_verified,
    }


@router.get("/usage", response_model=Usage)
async def usage(_: User = Depends(current_user)) -> Usage:
    queries = sum(r.retrieval_stats.queries_issued for r in REPO.runs.values())
    return Usage(
        runs_used=len(REPO.runs),
        queries_consumed=queries,
        prompt_tokens=LEDGER.prompt_tokens,
        completion_tokens=LEDGER.completion_tokens,
        estimated_cost_usd=round((LEDGER.prompt_tokens * 0.000002) + (LEDGER.completion_tokens * 0.00001), 4),
        by_stage=LEDGER.by_stage,
    )


@router.get("/replies", response_model=list[Reply])
async def replies(_: User = Depends(current_user)) -> list[Reply]:
    return sorted(REPO.replies.values(), key=lambda r: r.received_at, reverse=True)


@router.get("/pipeline", response_model=PipelineCounts)
async def pipeline_counts(_: User = Depends(current_user)) -> PipelineCounts:
    sent = sum(1 for s in REPO.sends.values() if s.status in ("delivered", "scheduled"))
    replied = len(REPO.replies)
    by_run: list[dict[str, float | str | int]] = []
    for run_id in REPO.runs:
        run_sends = [s for s in REPO.sends.values() if REPO.targets.get(s.target_id, None) and REPO.targets[s.target_id].run_id == run_id]
        if not run_sends:
            continue
        run_replies = sum(1 for r in REPO.replies.values() if REPO.targets.get(r.target_id) and REPO.targets[r.target_id].run_id == run_id)
        by_run.append(
            {
                "run_id": str(run_id),
                "sent": len(run_sends),
                "reply_rate": round(run_replies / len(run_sends), 3) if run_sends else 0.0,
            }
        )
    return PipelineCounts(sent=sent, replied=replied, meetings=sum(1 for r in REPO.replies.values() if r.sentiment == "positive"), by_run=by_run)


@router.get("/export/destinations", response_model=list[ExportDestination])
async def list_destinations(_: User = Depends(current_user)) -> list[ExportDestination]:
    return list(REPO.destinations.values())


@router.post("/export/destinations", response_model=ExportDestination, status_code=201)
async def add_destination(payload: ExportDestinationCreate, _: User = Depends(current_user)) -> ExportDestination:
    destination = ExportDestination(**payload.model_dump())
    REPO.destinations[destination.id] = destination
    return destination


@router.post("/runs/{run_id}/export", response_model=ExportResult)
async def export_run(run_id: UUID, destination_id: UUID, _: User = Depends(current_user)) -> ExportResult:
    if run_id not in REPO.runs:
        raise not_found("run", str(run_id))
    destination = REPO.destinations.get(destination_id)
    if not destination:
        raise not_found("destination", str(destination_id))

    rows = REPO.rows_for_run(run_id)
    values = [
        [
            row.investor_person or "",
            row.investor_firm,
            f"{row.score:.2f}",
            row.status,
            row.lead_evidence.claim,
            row.lead_evidence.source_url,
        ]
        for row in rows
    ]
    settings = get_settings()
    dry_run = not settings.composio_enabled
    if not dry_run:
        from ..composio_client import append_row, create_notion_page

        if destination.provider == "google_sheets":
            await append_row(destination.target_ref, values)
        else:
            await create_notion_page(destination.target_ref, f"Proofline run {run_id}", "\n".join(", ".join(v) for v in values))
    return ExportResult(
        destination_id=destination.id,
        rows_written=len(values),
        exported_at=utcnow(),
        provider=destination.provider,
        dry_run=dry_run,
    )
