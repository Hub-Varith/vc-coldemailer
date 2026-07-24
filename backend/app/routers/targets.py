from __future__ import annotations

import base64
import csv
import io
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse

from ..auth import current_user
from ..errors import ApiError, not_found
from ..models import (
    TargetListPage,
    TargetPatch,
    TargetRow,
    TargetSummary,
    User,
)
from ..store.repo import REPO

router = APIRouter(tags=["targets"])


def _summary(row: TargetRow) -> TargetSummary:
    return TargetSummary(
        target_id=row.target_id,
        run_id=row.run_id,
        investor_firm=row.investor_firm,
        investor_person=row.investor_person,
        role=row.role,
        score=row.score,
        status=row.status,
        contact_email=row.contact_email,
        firm_domain=row.firm_domain,
        evidence_count=len(row.evidence),
        has_stale_evidence=row.has_stale_evidence,
        lead_evidence=row.lead_evidence,
        location=row.location,
        check_min=row.check_min,
        check_max=row.check_max,
        stage=row.stage,
        sectors=row.sectors,
        draft_id=row.draft_id,
    )


def _get_target(target_id: UUID) -> TargetRow:
    row = REPO.targets.get(target_id)
    if not row:
        raise not_found("target", str(target_id))
    return row


@router.get("/runs/{run_id}/targets", response_model=TargetListPage)
async def list_targets(
    run_id: UUID,
    status: str | None = None,
    min_score: float | None = None,
    has_email: bool | None = None,
    stale: bool | None = None,
    sort: str = Query("score", pattern="^(score|firm|recency)$"),
    limit: int = 50,
    cursor: str | None = None,
    _: User = Depends(current_user),
) -> TargetListPage:
    if run_id not in REPO.runs:
        raise not_found("run", str(run_id))
    rows = [r for r in REPO.rows_for_run(run_id) if r.status != "dismissed" or status == "dismissed"]

    if status:
        rows = [r for r in rows if r.status == status]
    if min_score is not None:
        rows = [r for r in rows if r.score >= min_score]
    if has_email is not None:
        rows = [r for r in rows if bool(r.contact_email) is has_email]
    if stale is not None:
        rows = [r for r in rows if r.has_stale_evidence is stale]

    if sort == "firm":
        rows.sort(key=lambda r: r.investor_firm.lower())
    elif sort == "recency":
        rows.sort(key=lambda r: r.lead_evidence.effective_date or r.lead_evidence.verified_at.date(), reverse=True)  # type: ignore[union-attr]
    else:
        rows.sort(key=lambda r: -r.score)

    offset = 0
    if cursor:
        try:
            offset = int(base64.urlsafe_b64decode(cursor.encode()).decode())
        except (ValueError, UnicodeDecodeError):
            raise ApiError(400, "invalid_cursor", "Cursor is not a valid pagination token.")

    page = rows[offset : offset + limit]
    next_offset = offset + limit
    next_cursor = base64.urlsafe_b64encode(str(next_offset).encode()).decode() if next_offset < len(rows) else None
    return TargetListPage(
        rows=[_summary(r) for r in page],
        next_cursor=next_cursor,
        list_underfilled=any(r.list_underfilled for r in rows),
        total=len(rows),
    )


@router.get("/targets/{target_id}", response_model=TargetRow)
async def get_target(target_id: UUID, _: User = Depends(current_user)) -> TargetRow:
    return _get_target(target_id)


@router.patch("/targets/{target_id}", response_model=TargetRow)
async def patch_target(target_id: UUID, patch: TargetPatch, _: User = Depends(current_user)) -> TargetRow:
    row = _get_target(target_id)
    for field, value in patch.model_dump(exclude_none=True).items():
        setattr(row, field, value)
    return row


@router.post("/targets/{target_id}/dismiss", response_model=TargetRow)
async def dismiss_target(target_id: UUID, _: User = Depends(current_user)) -> TargetRow:
    row = _get_target(target_id)
    row.status = "dismissed"
    sequence = REPO.sequences.get(target_id)
    if sequence and sequence.state == "active":
        sequence.state = "stopped_manual"
        sequence.stop_reason = "Target dismissed"
        for step in sequence.steps:
            if step.status in ("pending", "scheduled"):
                step.status = "cancelled"
    return row


@router.get("/runs/{run_id}/targets/export")
async def export_targets(run_id: UUID, _: User = Depends(current_user)) -> StreamingResponse:
    if run_id not in REPO.runs:
        raise not_found("run", str(run_id))
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(
        ["person", "firm", "role", "score", "status", "contact_email", "lead_claim", "lead_date", "lead_source", "evidence_count"]
    )
    for row in sorted(REPO.rows_for_run(run_id), key=lambda r: -r.score):
        lead = row.lead_evidence
        writer.writerow(
            [
                row.investor_person or "",
                row.investor_firm,
                row.role or "",
                row.score,
                row.status,
                row.contact_email or "",
                lead.claim,
                lead.effective_date.isoformat() if lead.effective_date else "",
                lead.source_url,
                len(row.evidence),
            ]
        )
    buffer.seek(0)
    return StreamingResponse(
        iter([buffer.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="proofline-{run_id}.csv"'},
    )
