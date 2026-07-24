from __future__ import annotations

from fastapi import Header

from .config import get_settings
from .errors import ApiError
from .models import User
from .store.repo import REPO


async def current_user(authorization: str | None = Header(default=None)) -> User:
    """Bearer auth on everything except /auth/* and /health.

    In demo mode (`AUTH_OPTIONAL=true`, the default) an absent token resolves to the seeded
    founder so the frontend works without a login round-trip.
    """
    settings = get_settings()
    if authorization and authorization.lower().startswith("bearer "):
        token = authorization.split(" ", 1)[1].strip()
        user = REPO.user_for_token(token)
        if user:
            return user
        if not settings.auth_optional:
            raise ApiError(401, "invalid_token", "Session token is invalid or expired.")
    elif not settings.auth_optional:
        raise ApiError(401, "unauthorized", "Missing bearer token.")
    return REPO.demo_user
