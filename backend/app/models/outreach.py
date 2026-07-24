from __future__ import annotations

from datetime import date, datetime
from typing import Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from .profile import utcnow

Blocker = Literal["stale_lead_evidence", "no_contact_email", "prior_contact_exists", "domain_unverified"]
SequenceState = Literal["active", "stopped_reply", "stopped_manual", "complete"]
StepStatus = Literal["pending", "scheduled", "delivered", "cancelled", "failed"]


class PriorContact(BaseModel):
    found: bool = False
    last_thread_at: date | None = None
    summary: str | None = None


class DraftVersion(BaseModel):
    version: int
    subject: str
    body: str
    author: Literal["model", "human"]
    created_at: datetime = Field(default_factory=utcnow)
    angle: str | None = None


class Draft(BaseModel):
    draft_id: UUID = Field(default_factory=uuid4)
    target_id: UUID
    run_id: UUID
    subject: str
    body: str
    lead_evidence_id: UUID
    prior_contact: PriorContact = Field(default_factory=PriorContact)
    blockers: list[Blocker] = Field(default_factory=list)
    version: int = 1
    versions: list[DraftVersion] = Field(default_factory=list)
    approved_at: datetime | None = None
    approved_by: str | None = None
    updated_at: datetime = Field(default_factory=utcnow)
    generated_by: str = "deterministic"

    @property
    def word_count(self) -> int:
        return len([w for w in self.body.split() if w.strip()])

    @property
    def approved(self) -> bool:
        return self.approved_at is not None


class DraftPublic(BaseModel):
    draft_id: UUID
    target_id: UUID
    run_id: UUID
    subject: str
    body: str
    word_count: int
    lead_evidence_id: UUID
    prior_contact: PriorContact
    blockers: list[Blocker]
    version: int
    updated_at: datetime
    approved_at: datetime | None
    approved_by: str | None
    generated_by: str

    @classmethod
    def of(cls, draft: Draft) -> DraftPublic:
        return cls(
            draft_id=draft.draft_id,
            target_id=draft.target_id,
            run_id=draft.run_id,
            subject=draft.subject,
            body=draft.body,
            word_count=draft.word_count,
            lead_evidence_id=draft.lead_evidence_id,
            prior_contact=draft.prior_contact,
            blockers=draft.blockers,
            version=draft.version,
            updated_at=draft.updated_at,
            approved_at=draft.approved_at,
            approved_by=draft.approved_by,
            generated_by=draft.generated_by,
        )


class DraftPatch(BaseModel):
    subject: str | None = None
    body: str | None = None


class DraftRegenerate(BaseModel):
    tone: str | None = None
    angle: str | None = None


class ApprovalRequest(BaseModel):
    approved_by: str = "founder"
    note: str | None = None


class ScheduleRequest(BaseModel):
    send_at: datetime


class BulkSendRequest(BaseModel):
    draft_ids: list[UUID]


class Send(BaseModel):
    send_id: UUID = Field(default_factory=uuid4)
    draft_id: UUID
    target_id: UUID
    to_email: str
    from_email: str
    subject: str
    body: str
    status: Literal["queued", "scheduled", "delivered", "failed"] = "queued"
    provider: str = "composio.gmail"
    idempotency_key: str
    created_at: datetime = Field(default_factory=utcnow)
    scheduled_for: datetime | None = None
    delivered_at: datetime | None = None
    error: str | None = None


class SequenceStep(BaseModel):
    n: int
    offset_days: int
    channel: Literal["email", "linkedin"] = "email"
    intent: str = ""
    preview: str = ""
    scheduled_for: datetime | None = None
    sent_at: datetime | None = None
    status: StepStatus = "pending"


class Sequence(BaseModel):
    target_id: UUID
    draft_id: UUID | None = None
    state: SequenceState = "active"
    steps: list[SequenceStep] = Field(default_factory=list)
    stop_reason: str | None = None


class SequencePatch(BaseModel):
    offsets: list[int] | None = None


class Reply(BaseModel):
    reply_id: UUID = Field(default_factory=uuid4)
    target_id: UUID
    send_id: UUID
    investor_person: str | None
    investor_firm: str
    received_at: datetime
    snippet: str
    sentiment: Literal["positive", "neutral", "negative"] = "positive"


class PipelineCounts(BaseModel):
    sent: int = 0
    opened: int | None = None
    replied: int = 0
    meetings: int = 0
    by_run: list[dict[str, float | str | int]] = Field(default_factory=list)
