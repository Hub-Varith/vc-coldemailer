from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class CompanyProfile(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    company: str
    round: str
    raise_target: str
    one_liner: str
    sectors: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)
    geographies: list[str] = Field(default_factory=list)
    check_target_min: int = 250_000
    check_target_max: int = 2_000_000
    traction: list[str] = Field(default_factory=list)
    founder_name: str = ""
    founder_email: str = ""
    founder_affinities: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)


class CompanyProfileCreate(BaseModel):
    company: str
    round: str = "Seed"
    raise_target: str = ""
    one_liner: str = ""
    sectors: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)
    geographies: list[str] = Field(default_factory=list)
    check_target_min: int = 250_000
    check_target_max: int = 2_000_000
    traction: list[str] = Field(default_factory=list)
    founder_name: str = ""
    founder_email: str = ""
    founder_affinities: list[str] = Field(default_factory=list)


class CompanyProfilePatch(BaseModel):
    company: str | None = None
    round: str | None = None
    raise_target: str | None = None
    one_liner: str | None = None
    sectors: list[str] | None = None
    keywords: list[str] | None = None
    geographies: list[str] | None = None
    check_target_min: int | None = None
    check_target_max: int | None = None
    traction: list[str] | None = None
    founder_name: str | None = None
    founder_email: str | None = None
    founder_affinities: list[str] | None = None


class ProfileValidation(BaseModel):
    ok: bool
    warnings: list[str] = Field(default_factory=list)
    suggestions: list[str] = Field(default_factory=list)
