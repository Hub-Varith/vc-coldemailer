from __future__ import annotations

from fastapi import APIRouter, Depends

from ..auth import current_user
from ..config import get_settings
from ..errors import ApiError
from ..models import (
    ConnectResponse,
    Integration,
    LoginRequest,
    Provider,
    Session,
    User,
    UserPatch,
    utcnow,
)
from ..store.repo import REPO

router = APIRouter(tags=["account"])


@router.post("/auth/login", response_model=Session)
async def login(payload: LoginRequest) -> Session:
    user = next((u for u in REPO.users.values() if u.email == payload.email), None) or REPO.demo_user
    return REPO.issue_session(user)


@router.post("/auth/logout")
async def logout(authorization: str | None = None) -> dict[str, bool]:
    if authorization and authorization.lower().startswith("bearer "):
        REPO.sessions.pop(authorization.split(" ", 1)[1].strip(), None)
    return {"ok": True}


@router.get("/me", response_model=User)
async def me(user: User = Depends(current_user)) -> User:
    return user


@router.patch("/me", response_model=User)
async def patch_me(patch: UserPatch, user: User = Depends(current_user)) -> User:
    for field, value in patch.model_dump(exclude_none=True).items():
        setattr(user, field, value)
    return user


@router.get("/integrations")
async def list_integrations(_: User = Depends(current_user)) -> dict[str, list[Integration]]:
    return {"integrations": list(REPO.integrations.values())}


@router.post("/integrations/{provider}/connect", response_model=ConnectResponse)
async def connect(provider: Provider, _: User = Depends(current_user)) -> ConnectResponse:
    integration = REPO.integrations.get(provider)
    if not integration:
        raise ApiError(404, "provider_not_found", f"Unknown provider {provider}.")
    integration.status = "pending"
    integration.error_reason = None
    connection_id = f"conn_{provider}_{int(utcnow().timestamp())}"
    settings = get_settings()
    base = "https://backend.composio.dev/oauth" if settings.composio_enabled else "http://localhost:8000/api/v1/integrations"
    return ConnectResponse(redirect_url=f"{base}/{provider}/authorize?connection_id={connection_id}", connection_id=connection_id)


@router.get("/integrations/{provider}/status", response_model=Integration)
async def integration_status(provider: Provider, _: User = Depends(current_user)) -> Integration:
    integration = REPO.integrations.get(provider)
    if not integration:
        raise ApiError(404, "provider_not_found", f"Unknown provider {provider}.")
    if integration.status == "pending":
        integration.status = "connected"
        integration.scopes_ok = True
        integration.connected_at = utcnow()
        integration.account = get_settings().composio_user_id
    return integration


@router.delete("/integrations/{provider}", response_model=Integration)
async def disconnect(provider: Provider, _: User = Depends(current_user)) -> Integration:
    integration = REPO.integrations.get(provider)
    if not integration:
        raise ApiError(404, "provider_not_found", f"Unknown provider {provider}.")
    integration.status = "disconnected"
    integration.account = None
    integration.scopes_ok = False
    integration.connected_at = None
    return integration
