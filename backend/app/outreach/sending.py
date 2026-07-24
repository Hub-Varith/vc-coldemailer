"""Sending and sequencing.

Two rules the API enforces so the frontend cannot bypass them (API_ENDPOINTS §7):
approval is per-message and required, and sends are rejected when the sending domain is
unverified. Sends are idempotent on `Idempotency-Key` — a double-send is unrecoverable.
"""

from __future__ import annotations

import logging
from datetime import datetime, time, timedelta, timezone

from ..config import get_settings
from ..errors import ApiError
from ..models import (
    CompanyProfile,
    Draft,
    Send,
    Sequence,
    SequenceStep,
    TargetRow,
)
from ..store.repo import REPO

log = logging.getLogger("proofline.outreach.sending")

DEFAULT_OFFSETS = (4, 10)
_STEP_INTENTS = {
    4: ("Add proof point", "Reply-to-self with the strongest supporting fact and the trial readout."),
    10: ("Close the loop", "One line: a yes, a no, or the right person on the team — all three are useful."),
}


def build_sequence(target_id, draft_id, offsets: tuple[int, ...] = DEFAULT_OFFSETS) -> Sequence:
    steps = [SequenceStep(n=1, offset_days=0, intent="Initial send", preview="The approved message.")]
    for index, offset in enumerate(offsets, start=2):
        intent, preview = _STEP_INTENTS.get(offset, ("Follow-up", "Short follow-up on the original thread."))
        steps.append(SequenceStep(n=index, offset_days=offset, intent=intent, preview=preview))
    return Sequence(target_id=target_id, draft_id=draft_id, steps=steps)


def schedule_steps(sequence: Sequence, sent_at: datetime) -> Sequence:
    for step in sequence.steps:
        if step.n == 1:
            step.sent_at = sent_at
            step.status = "delivered"
            continue
        at = sent_at + timedelta(days=step.offset_days)
        step.scheduled_for = datetime.combine(at.date(), time(9, 0), tzinfo=timezone.utc)
        step.status = "scheduled"
    return sequence


def assert_sendable(draft: Draft, row: TargetRow) -> None:
    settings = get_settings()
    if not settings.sending_domain_verified:
        raise ApiError(409, "domain_unverified", "Sending domain is not verified. Verify the domain before sending.")
    if not draft.approved:
        raise ApiError(
            409,
            "draft_not_approved",
            "This draft has not been approved. Nothing sends without a per-message approval.",
            {"draft_id": str(draft.draft_id)},
        )
    blocking = [b for b in draft.blockers if b != "prior_contact_exists"]
    if blocking:
        raise ApiError(409, "draft_blocked", "This draft has unresolved blockers.", {"blockers": blocking})
    if not row.contact_email:
        raise ApiError(409, "no_contact_email", "No contact address resolved for this investor.")


async def deliver(draft: Draft, row: TargetRow, profile: CompanyProfile, idempotency_key: str, when: datetime | None = None) -> Send:
    """Own-domain delivery through Composio. Records the send even when the provider is off."""
    existing_id = REPO.sends_by_idempotency.get(idempotency_key)
    if existing_id:
        return REPO.sends[existing_id]

    settings = get_settings()
    assert_sendable(draft, row)
    from_email = profile.founder_email or f"founder@{settings.sending_domain}"
    send = Send(
        draft_id=draft.draft_id,
        target_id=row.target_id,
        to_email=row.contact_email or "",
        from_email=from_email,
        subject=draft.subject,
        body=draft.body,
        idempotency_key=idempotency_key,
        scheduled_for=when,
        status="scheduled" if when else "queued",
    )

    if when is None:
        if settings.composio_enabled:
            try:
                from ..composio_client import send_email

                await send_email(to=send.to_email, subject=send.subject, body=send.body, from_email=from_email)
                send.status = "delivered"
                send.delivered_at = datetime.now(timezone.utc)
            except Exception as exc:
                log.warning("composio send failed: %s", exc)
                send.status = "failed"
                send.error = str(exc)
        else:
            send.status = "delivered"
            send.delivered_at = datetime.now(timezone.utc)
            send.provider = "local.no_provider"

    REPO.sends[send.send_id] = send
    REPO.sends_by_idempotency[idempotency_key] = send.send_id

    sequence = REPO.sequences.get(row.target_id) or build_sequence(row.target_id, draft.draft_id)
    REPO.sequences[row.target_id] = schedule_steps(sequence, send.delivered_at or send.scheduled_for or datetime.now(timezone.utc))
    row.status = "sent"
    return send
