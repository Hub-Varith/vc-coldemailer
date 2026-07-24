"""Seed the demo workspace: one founder, one profile, integration state.

Called on startup so the frontend has something to open onto before the first run.
"""

from __future__ import annotations

from uuid import UUID

from .config import get_settings
from .models import CompanyProfile, Integration, User
from .store.repo import REPO

DEMO_PROFILE_ID = UUID("c0ffee00-0000-4000-8000-000000000001")

DEMO_PROFILE = CompanyProfile(
    id=DEMO_PROFILE_ID,
    company="Novi Audio",
    round="Seed",
    raise_target="$3.5M",
    one_liner="Bone-conduction hearing hardware for the 1.5B people priced out of clinical audiology.",
    sectors=["hearing", "audio hardware", "accessibility", "health infra"],
    keywords=[
        "bone conduction",
        "hearing",
        "wearable audio",
        "cash-pay medical device",
        "contract manufacturing",
        "accessibility hardware",
    ],
    geographies=["US", "EU"],
    check_target_min=250_000,
    check_target_max=2_000_000,
    traction=["a $180 bill of materials", "240 users in Lisbon field trials", "78% retention at day 90"],
    founder_name="Ines Duarte",
    founder_email="ines@noviaudio.com",
    founder_affinities=["Lisbon", "IST", "hardware operator"],
)


def seed() -> None:
    if REPO.users:
        return
    settings = get_settings()
    user = User(
        email="ines@noviaudio.com",
        display_name="Ines Duarte",
        org="Novi Audio",
        sending_name="Ines Duarte",
        signature_block="Ines Duarte — Novi Audio",
        sending_domain=settings.sending_domain,
        sending_domain_verified=settings.sending_domain_verified,
        feature_flags={"live_search": True, "sequences": True},
    )
    REPO.users[user.id] = user
    REPO.profiles[DEMO_PROFILE.id] = DEMO_PROFILE.model_copy(deep=True)
    REPO.integrations = {
        "gmail": Integration(
            provider="gmail",
            status="connected" if settings.composio_enabled else "disconnected",
            account=settings.composio_user_id if settings.composio_enabled else None,
            scopes_ok=settings.composio_enabled,
        ),
        "google_sheets": Integration(provider="google_sheets", status="disconnected"),
        "notion": Integration(provider="notion", status="disconnected"),
    }
