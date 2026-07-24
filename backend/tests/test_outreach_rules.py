"""Approval, idempotency and send-gate rules — the product's non-negotiables."""

from datetime import date, datetime, timezone
from uuid import uuid4

import pytest

from app.errors import ApiError
from app.models import EvidenceRecord, TargetRow
from app.outreach.drafting import build_draft, deterministic_draft
from app.outreach.sending import assert_sendable, build_sequence, deliver, schedule_steps
from app.store.repo import REPO


def _row(**overrides) -> TargetRow:
    lead = EvidenceRecord(
        investor_firm="Overture Capital",
        investor_person="Elias Lind",
        kind="thesis_publication",
        claim="Argued on the Northbound podcast that hearables are the next platform shift.",
        detail="Flags medical-adjacent hearables as the segment he wants to own.",
        event_date=date(2026, 4, 19),
        source_url="https://northbound.fm/episodes/112-elias-lind",
        source_name="Northbound Podcast — Episode 112",
        confidence=0.85,
    )
    base = dict(
        run_id=uuid4(),
        investor_firm="Overture Capital",
        investor_person="Elias Lind",
        role="Partner",
        score=0.92,
        evidence=[lead],
        lead_evidence=lead,
        contact_email="elias@overturecapital.com",
    )
    base.update(overrides)
    return TargetRow(**base)


def test_draft_opens_from_the_lead_fact_and_fits_the_word_band(profile):
    row = _row()
    subject, body = deterministic_draft(row, profile)
    words = len(body.split())

    assert 80 <= words <= 120, f"drafts are 80-120 words, got {words}"
    assert "Northbound" in body, "the email opens from the qualifying evidence, not a template"
    assert profile.traction[0] in body, "a defensible number is present"
    assert subject and len(subject) < 90


@pytest.mark.asyncio
async def test_stale_lead_evidence_blocks_the_draft(profile):
    lead = EvidenceRecord(
        investor_firm="Overture Capital",
        investor_person="Elias Lind",
        kind="portfolio_investment",
        claim="Led a pre-seed round.",
        event_date=date(2024, 1, 1),
        source_url="https://example.com/x",
        stale=True,
    )
    draft = await build_draft(_row(evidence=[lead], lead_evidence=lead), profile)
    assert "stale_lead_evidence" in draft.blockers


@pytest.mark.asyncio
async def test_prior_contact_is_surfaced_not_silently_ignored(profile):
    row = _row(investor_person="Marcus Reyes", investor_firm="Foundry Line")
    draft = await build_draft(row, profile)
    assert draft.prior_contact.found is True
    assert "prior_contact_exists" in draft.blockers


@pytest.mark.asyncio
async def test_send_requires_approval(profile):
    row = _row()
    draft = await build_draft(row, profile)
    with pytest.raises(ApiError) as excinfo:
        assert_sendable(draft, row)
    assert excinfo.value.code == "draft_not_approved"
    assert excinfo.value.status_code == 409


@pytest.mark.asyncio
async def test_send_is_idempotent_on_key(profile):
    REPO.sends.clear()
    REPO.sends_by_idempotency.clear()
    row = _row()
    draft = await build_draft(row, profile)
    draft.blockers = []
    draft.approved_at = datetime.now(timezone.utc)
    draft.approved_by = "founder"

    first = await deliver(draft, row, profile, "key-1")
    second = await deliver(draft, row, profile, "key-1")
    assert first.send_id == second.send_id, "a double-send is unrecoverable; the key must dedupe"
    assert len(REPO.sends) == 1


@pytest.mark.asyncio
async def test_send_is_from_the_founders_own_domain(profile):
    REPO.sends.clear()
    REPO.sends_by_idempotency.clear()
    row = _row()
    draft = await build_draft(row, profile)
    draft.blockers = []
    draft.approved_at = datetime.now(timezone.utc)

    send = await deliver(draft, row, profile, "key-2")
    assert send.from_email.endswith("noviaudio.com")


def test_sequence_schedules_day_four_and_day_ten():
    sequence = schedule_steps(build_sequence(uuid4(), uuid4()), datetime(2026, 7, 23, 9, 0, tzinfo=timezone.utc))
    offsets = [step.offset_days for step in sequence.steps]
    assert offsets == [0, 4, 10]
    assert sequence.steps[0].status == "delivered"
    assert sequence.steps[1].scheduled_for is not None
    assert sequence.steps[1].scheduled_for.day == 27
