"""In-memory persistence.

Deliberately a single seam: swap this class for SQLAlchemy async and nothing above it
changes. Everything is keyed by UUID and guarded by an asyncio lock.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

from ..models import (
    CompanyProfile,
    Draft,
    ExportDestination,
    Integration,
    Reply,
    Run,
    SearchPlan,
    Send,
    Sequence,
    Session,
    TargetRow,
    User,
)


class Repository:
    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self.users: dict[UUID, User] = {}
        self.sessions: dict[str, Session] = {}
        self.profiles: dict[UUID, CompanyProfile] = {}
        self.runs: dict[UUID, Run] = {}
        self.plans: dict[UUID, SearchPlan] = {}
        self.targets: dict[UUID, TargetRow] = {}
        self.targets_by_run: dict[UUID, list[UUID]] = {}
        self.warnings: dict[UUID, list[str]] = {}
        self.drafts: dict[UUID, Draft] = {}
        self.drafts_by_target: dict[UUID, UUID] = {}
        self.sends: dict[UUID, Send] = {}
        self.sends_by_idempotency: dict[str, UUID] = {}
        self.sequences: dict[UUID, Sequence] = {}
        self.replies: dict[UUID, Reply] = {}
        self.integrations: dict[str, Integration] = {}
        self.destinations: dict[UUID, ExportDestination] = {}
        self.cancelled_runs: set[UUID] = set()

    # -- users & sessions -------------------------------------------------
    def issue_session(self, user: User, ttl_hours: int = 24) -> Session:
        session = Session(
            token=uuid4().hex,
            user_id=user.id,
            expires_at=datetime.now(timezone.utc) + timedelta(hours=ttl_hours),
        )
        self.sessions[session.token] = session
        return session

    def user_for_token(self, token: str) -> User | None:
        session = self.sessions.get(token)
        if not session or session.expires_at < datetime.now(timezone.utc):
            return None
        return self.users.get(session.user_id)

    @property
    def demo_user(self) -> User:
        return next(iter(self.users.values()))

    # -- runs & targets ---------------------------------------------------
    async def save_run(self, run: Run) -> Run:
        async with self._lock:
            self.runs[run.run_id] = run
        return run

    async def put_targets(self, run_id: UUID, rows: list[TargetRow]) -> None:
        async with self._lock:
            self.targets_by_run[run_id] = [row.target_id for row in rows]
            for row in rows:
                self.targets[row.target_id] = row

    def rows_for_run(self, run_id: UUID) -> list[TargetRow]:
        return [self.targets[tid] for tid in self.targets_by_run.get(run_id, []) if tid in self.targets]

    def latest_run(self) -> Run | None:
        runs = sorted(self.runs.values(), key=lambda r: r.started_at, reverse=True)
        return runs[0] if runs else None

    def draft_for_target(self, target_id: UUID) -> Draft | None:
        draft_id = self.drafts_by_target.get(target_id)
        return self.drafts.get(draft_id) if draft_id else None

    def save_draft(self, draft: Draft) -> Draft:
        self.drafts[draft.draft_id] = draft
        self.drafts_by_target[draft.target_id] = draft.draft_id
        return draft

    def delete_run(self, run_id: UUID) -> None:
        for target_id in self.targets_by_run.pop(run_id, []):
            target = self.targets.pop(target_id, None)
            if not target:
                continue
            draft_id = self.drafts_by_target.pop(target_id, None)
            if draft_id:
                self.drafts.pop(draft_id, None)
            self.sequences.pop(target_id, None)
        self.runs.pop(run_id, None)
        self.plans.pop(run_id, None)
        self.warnings.pop(run_id, None)


REPO = Repository()
