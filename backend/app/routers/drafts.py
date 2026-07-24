from __future__ import annotations

import asyncio
from uuid import UUID

from fastapi import APIRouter, Depends

from ..auth import current_user
from ..errors import ApiError, not_found
from ..models import (
    ApprovalRequest,
    Draft,
    DraftPatch,
    DraftPublic,
    DraftRegenerate,
    DraftVersion,
    TargetRow,
    User,
    utcnow,
)
from ..outreach.drafting import build_draft, generate_draft_content
from ..outreach.sending import build_sequence
from ..store.repo import REPO

router = APIRouter(tags=["drafts"])


def _profile_for(row: TargetRow):
    run = REPO.runs.get(row.run_id)
    profile = REPO.profiles.get(run.profile_id) if run else None
    if not profile:
        raise not_found("profile", str(row.run_id))
    return profile


def _get_draft(draft_id: UUID) -> Draft:
    draft = REPO.drafts.get(draft_id)
    if not draft:
        raise not_found("draft", str(draft_id))
    return draft


async def draft_for_row(row: TargetRow) -> Draft:
    existing = REPO.draft_for_target(row.target_id)
    if existing:
        return existing
    draft = await build_draft(row, _profile_for(row))
    REPO.save_draft(draft)
    row.draft_id = draft.draft_id
    row.status = "needs_review" if "stale_lead_evidence" in draft.blockers else "drafted"
    return draft


@router.post("/targets/{target_id}/draft", response_model=DraftPublic, status_code=201)
async def create_draft(target_id: UUID, _: User = Depends(current_user)) -> DraftPublic:
    row = REPO.targets.get(target_id)
    if not row:
        raise not_found("target", str(target_id))
    return DraftPublic.of(await draft_for_row(row))


@router.post("/runs/{run_id}/drafts/bulk", status_code=202)
async def bulk_draft(run_id: UUID, limit: int = 25, _: User = Depends(current_user)) -> dict[str, int | str]:
    if run_id not in REPO.runs:
        raise not_found("run", str(run_id))
    rows = [r for r in REPO.rows_for_run(run_id) if not REPO.draft_for_target(r.target_id)][:limit]
    asyncio.create_task(_bulk_draft_task(rows))
    return {"run_id": str(run_id), "queued": len(rows)}


async def _bulk_draft_task(rows: list[TargetRow]) -> None:
    for row in rows:
        await draft_for_row(row)


@router.get("/drafts/{draft_id}", response_model=DraftPublic)
async def get_draft(draft_id: UUID, _: User = Depends(current_user)) -> DraftPublic:
    return DraftPublic.of(_get_draft(draft_id))


@router.patch("/drafts/{draft_id}", response_model=DraftPublic)
async def patch_draft(draft_id: UUID, patch: DraftPatch, _: User = Depends(current_user)) -> DraftPublic:
    """Human edits always win — an edit resets approval so nothing sends unreviewed."""
    draft = _get_draft(draft_id)
    changed = False
    if patch.subject is not None and patch.subject != draft.subject:
        draft.subject = patch.subject
        changed = True
    if patch.body is not None and patch.body != draft.body:
        draft.body = patch.body
        changed = True
    if changed:
        draft.version += 1
        draft.versions.append(
            DraftVersion(version=draft.version, subject=draft.subject, body=draft.body, author="human")
        )
        draft.updated_at = utcnow()
        if draft.approved:
            draft.approved_at = None
            draft.approved_by = None
            row = REPO.targets.get(draft.target_id)
            if row and row.status == "approved":
                row.status = "drafted"
    return DraftPublic.of(draft)


@router.post("/drafts/{draft_id}/regenerate", response_model=DraftPublic)
async def regenerate(draft_id: UUID, payload: DraftRegenerate, _: User = Depends(current_user)) -> DraftPublic:
    draft = _get_draft(draft_id)
    row = REPO.targets.get(draft.target_id)
    if not row:
        raise not_found("target", str(draft.target_id))
    angle = payload.angle or payload.tone
    subject, body, generated_by = await generate_draft_content(row, _profile_for(row), angle)
    draft.subject, draft.body, draft.generated_by = subject, body, generated_by
    draft.version += 1
    draft.versions.append(DraftVersion(version=draft.version, subject=subject, body=body, author="model", angle=angle))
    draft.approved_at = None
    draft.approved_by = None
    draft.updated_at = utcnow()
    return DraftPublic.of(draft)


@router.get("/drafts/{draft_id}/versions", response_model=list[DraftVersion])
async def draft_versions(draft_id: UUID, _: User = Depends(current_user)) -> list[DraftVersion]:
    return _get_draft(draft_id).versions


@router.post("/drafts/{draft_id}/approve", response_model=DraftPublic)
async def approve(draft_id: UUID, payload: ApprovalRequest, _: User = Depends(current_user)) -> DraftPublic:
    """Marks approved. Does not send — sending is a separate, explicit call."""
    draft = _get_draft(draft_id)
    blocking = [b for b in draft.blockers if b != "prior_contact_exists"]
    if blocking:
        raise ApiError(409, "draft_blocked", "Resolve blockers before approving.", {"blockers": blocking})
    draft.approved_at = utcnow()
    draft.approved_by = payload.approved_by
    draft.updated_at = draft.approved_at
    row = REPO.targets.get(draft.target_id)
    if row:
        row.status = "approved"
        if row.target_id not in REPO.sequences:
            REPO.sequences[row.target_id] = build_sequence(row.target_id, draft.draft_id)
    return DraftPublic.of(draft)


@router.get("/queue", response_model=list[DraftPublic])
async def approval_queue(status: str | None = None, _: User = Depends(current_user)) -> list[DraftPublic]:
    drafts = list(REPO.drafts.values())
    if status == "approved":
        drafts = [d for d in drafts if d.approved]
    elif status == "pending":
        drafts = [d for d in drafts if not d.approved]
    return [DraftPublic.of(d) for d in sorted(drafts, key=lambda d: d.updated_at, reverse=True)]
