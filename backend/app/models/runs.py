from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from .profile import utcnow
from .retrieval import RetrievalStats

RunStage = Literal[
    "queued", "planning", "retrieving", "extracting", "verifying", "scoring", "complete", "failed", "cancelled"
]
RunStatus = Literal["queued", "running", "complete", "failed", "cancelled"]


class RunProgress(BaseModel):
    queries_total: int = 0
    queries_done: int = 0
    results: int = 0
    evidence: int = 0
    investors: int = 0


class Run(BaseModel):
    run_id: UUID = Field(default_factory=uuid4)
    profile_id: UUID
    status: RunStatus = "queued"
    stage: RunStage = "queued"
    progress: RunProgress = Field(default_factory=RunProgress)
    retrieval_stats: RetrievalStats = Field(default_factory=RetrievalStats)
    warnings: list[str] = Field(default_factory=list)
    started_at: datetime = Field(default_factory=utcnow)
    completed_at: datetime | None = None
    list_underfilled: bool = False
    rejected_count: int = 0
    sources_searched: int = 0
    error: str | None = None


class RunCreate(BaseModel):
    profile_id: UUID | None = None


class RunEvent(BaseModel):
    """SSE payload (API_ENDPOINTS §4)."""

    type: Literal[
        "stage_changed",
        "query_batch_done",
        "investor_found",
        "record_rejected",
        "run_complete",
        "run_failed",
        "heartbeat",
    ]
    run_id: UUID
    at: datetime = Field(default_factory=utcnow)
    stage: RunStage | None = None
    message: str | None = None
    data: dict = Field(default_factory=dict)


class Usage(BaseModel):
    runs_used: int = 0
    queries_consumed: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    estimated_cost_usd: float = 0.0
    by_stage: dict[str, dict[str, int]] = Field(default_factory=dict)
