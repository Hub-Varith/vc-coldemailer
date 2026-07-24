from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Header

from ..auth import current_user
from ..errors import ApiError, not_found
from ..models import (
    BulkSendRequest,
    ScheduleRequest,
    Send,
    Sequence,
    SequencePatch,
    User,
)
from ..outreach.sending import build_sequence, deliver, schedule_steps
from ..store.repo import REPO

router = APIRouter(tags=["sends"])


def _require_idempotency(key: str | None) -> str:
    if not key:
        raise ApiError(
            400,
            "idempotency_key_required",
            "Send operations require an Idempotency-Key header. A double-send is unrecoverable.",
        )
    return key


def _draft_and_row(draft_id: UUID):
    draft = REPO.drafts.get(draft_id)
    if not draft:
        raise not_found("draft", str(draft_id))
    row = REPO.targets.get(draft.target_id)
    if not row:
        raise not_found("target", str(draft.target_id))
    run = REPO.runs.get(row.run_id)
    profile = REPO.profiles.get(run.profile_id) if run else None
    if not profile:
        raise not_found("profile", str(row.run_id))
    return draft, row, profile


@router.post("/drafts/{draft_id}/send", response_model=Send)
async def send_now(
    draft_id: UUID,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    _: User = Depends(current_user),
) -> Send:
    draft, row, profile = _draft_and_row(draft_id)
    return await deliver(draft, row, profile, _require_idempotency(idempotency_key))


@router.post("/drafts/{draft_id}/schedule", response_model=Send)
async def schedule_send(
    draft_id: UUID,
    payload: ScheduleRequest,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    _: User = Depends(current_user),
) -> Send:
    draft, row, profile = _draft_and_row(draft_id)
    return await deliver(draft, row, profile, _require_idempotency(idempotency_key), when=payload.send_at)


@router.post("/sends/bulk", response_model=list[Send])
async def send_bulk(
    payload: BulkSendRequest,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    _: User = Depends(current_user),
) -> list[Send]:
    """Rejects any draft not individually approved. Bulk approval is deliberately not offered."""
    key = _require_idempotency(idempotency_key)
    unapproved = [str(d) for d in payload.draft_ids if not (REPO.drafts.get(d) and REPO.drafts[d].approved)]
    if unapproved:
        raise ApiError(
            409,
            "unapproved_drafts",
            "Every message must be approved individually before a bulk send.",
            {"draft_ids": unapproved},
        )
    sends: list[Send] = []
    for draft_id in payload.draft_ids:
        draft, row, profile = _draft_and_row(draft_id)
        sends.append(await deliver(draft, row, profile, f"{key}:{draft_id}"))
    return sends


@router.get("/sends/{send_id}", response_model=Send)
async def get_send(send_id: UUID, _: User = Depends(current_user)) -> Send:
    send = REPO.sends.get(send_id)
    if not send:
        raise not_found("send", str(send_id))
    return send


@router.get("/sequences/{target_id}", response_model=Sequence)
async def get_sequence(target_id: UUID, _: User = Depends(current_user)) -> Sequence:
    sequence = REPO.sequences.get(target_id)
    if not sequence:
        row = REPO.targets.get(target_id)
        if not row:
            raise not_found("target", str(target_id))
        draft = REPO.draft_for_target(target_id)
        sequence = build_sequence(target_id, draft.draft_id if draft else None)
        REPO.sequences[target_id] = sequence
    return sequence


@router.post("/sequences/{target_id}/cancel", response_model=Sequence)
async def cancel_sequence(target_id: UUID, _: User = Depends(current_user)) -> Sequence:
    sequence = REPO.sequences.get(target_id)
    if not sequence:
        raise not_found("sequence", str(target_id))
    sequence.state = "stopped_manual"
    sequence.stop_reason = "Stopped by the founder"
    for step in sequence.steps:
        if step.status in ("pending", "scheduled"):
            step.status = "cancelled"
    return sequence


@router.patch("/sequences/{target_id}", response_model=Sequence)
async def patch_sequence(target_id: UUID, patch: SequencePatch, _: User = Depends(current_user)) -> Sequence:
    sequence = REPO.sequences.get(target_id)
    if not sequence:
        raise not_found("sequence", str(target_id))
    if patch.offsets:
        first = sequence.steps[0]
        rebuilt = build_sequence(target_id, sequence.draft_id, tuple(patch.offsets))
        rebuilt.steps[0] = first
        if first.sent_at:
            rebuilt = schedule_steps(rebuilt, first.sent_at)
        rebuilt.state = sequence.state
        REPO.sequences[target_id] = rebuilt
        return rebuilt
    return sequence
