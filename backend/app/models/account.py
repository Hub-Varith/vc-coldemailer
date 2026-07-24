from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from .profile import utcnow

Provider = Literal["gmail", "google_sheets", "notion"]
IntegrationStatus = Literal["disconnected", "pending", "connected", "error"]


class User(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    email: str
    display_name: str
    org: str
    plan: str = "hackathon"
    sending_name: str = ""
    signature_block: str = ""
    sending_domain: str = "noviaudio.com"
    sending_domain_verified: bool = True
    feature_flags: dict[str, bool] = Field(default_factory=dict)


class UserPatch(BaseModel):
    display_name: str | None = None
    sending_name: str | None = None
    signature_block: str | None = None


class LoginRequest(BaseModel):
    email: str
    password: str | None = None
    magic_link: bool = False


class Session(BaseModel):
    token: str
    user_id: UUID
    expires_at: datetime
    issued_at: datetime = Field(default_factory=utcnow)


class Integration(BaseModel):
    provider: Provider
    status: IntegrationStatus = "disconnected"
    account: str | None = None
    scopes_ok: bool = False
    connected_at: datetime | None = None
    error_reason: str | None = None


class ConnectResponse(BaseModel):
    redirect_url: str
    connection_id: str


class ExportDestination(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    provider: Literal["google_sheets", "notion"]
    name: str
    target_ref: str
    created_at: datetime = Field(default_factory=utcnow)


class ExportDestinationCreate(BaseModel):
    provider: Literal["google_sheets", "notion"]
    name: str
    target_ref: str


class ExportResult(BaseModel):
    destination_id: UUID
    rows_written: int
    exported_at: datetime
    provider: str
    dry_run: bool = False
