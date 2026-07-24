from __future__ import annotations

from typing import Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

IntentKind = Literal[
    "adjacent_portfolio",
    "thesis_signal",
    "fund_activity",
    "geo_crossing",
    "portfolio_gap",
    "recent_exit",
]


class SearchIntent(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    kind: IntentKind
    rationale: str
    queries: list[str]
    domain_hints: list[str] = Field(default_factory=list)
    recency_days: int | None = None


class SearchPlan(BaseModel):
    profile_id: UUID
    intents: list[SearchIntent]
    generated_by: str = "deterministic"

    @property
    def query_count(self) -> int:
        return sum(len(i.queries) for i in self.intents)
