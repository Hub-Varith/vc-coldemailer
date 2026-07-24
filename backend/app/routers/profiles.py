from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends

from ..errors import not_found
from ..auth import current_user
from ..models import (
    CompanyProfile,
    CompanyProfileCreate,
    CompanyProfilePatch,
    ProfileValidation,
    User,
    utcnow,
)
from ..store.repo import REPO

router = APIRouter(prefix="/profiles", tags=["profiles"])

BROAD_SECTORS = {"medtech", "health", "healthcare", "hardware", "consumer", "ai", "software", "tech"}


@router.post("", response_model=CompanyProfile, status_code=201)
async def create_profile(payload: CompanyProfileCreate, _: User = Depends(current_user)) -> CompanyProfile:
    profile = CompanyProfile(**payload.model_dump())
    REPO.profiles[profile.id] = profile
    return profile


@router.get("", response_model=list[CompanyProfile])
async def list_profiles(_: User = Depends(current_user)) -> list[CompanyProfile]:
    return sorted(REPO.profiles.values(), key=lambda p: p.created_at, reverse=True)


@router.get("/{profile_id}", response_model=CompanyProfile)
async def get_profile(profile_id: UUID, _: User = Depends(current_user)) -> CompanyProfile:
    profile = REPO.profiles.get(profile_id)
    if not profile:
        raise not_found("profile", str(profile_id))
    return profile


@router.patch("/{profile_id}", response_model=CompanyProfile)
async def patch_profile(
    profile_id: UUID, patch: CompanyProfilePatch, _: User = Depends(current_user)
) -> CompanyProfile:
    profile = REPO.profiles.get(profile_id)
    if not profile:
        raise not_found("profile", str(profile_id))
    for field, value in patch.model_dump(exclude_none=True).items():
        setattr(profile, field, value)
    profile.updated_at = utcnow()
    return profile


@router.delete("/{profile_id}", status_code=204)
async def delete_profile(profile_id: UUID, _: User = Depends(current_user)) -> None:
    if profile_id not in REPO.profiles:
        raise not_found("profile", str(profile_id))
    del REPO.profiles[profile_id]


@router.post("/{profile_id}/validate", response_model=ProfileValidation)
async def validate_profile(profile_id: UUID, _: User = Depends(current_user)) -> ProfileValidation:
    """Cheap pre-flight so a vague profile does not burn a 400-query run."""
    profile = REPO.profiles.get(profile_id)
    if not profile:
        raise not_found("profile", str(profile_id))

    warnings: list[str] = []
    suggestions: list[str] = []
    if not profile.sectors or all(s.lower() in BROAD_SECTORS for s in profile.sectors):
        warnings.append("sector_too_broad")
        suggestions.append("Name the specific product category, not just 'medtech'.")
    if not profile.round:
        warnings.append("no_stage_specified")
        suggestions.append("State the round — seed and Series A pull entirely different lists.")
    if len(profile.keywords) < 3:
        warnings.append("thin_keywords")
        suggestions.append("Add at least three concrete category phrases a partner would actually write.")
    if not profile.traction:
        warnings.append("no_traction_facts")
        suggestions.append("Add one number the email can defend — retention, users, unit cost.")
    if len(profile.one_liner.split()) < 8:
        warnings.append("positioning_vague")
        suggestions.append("Say who the customer is and what the product replaces, in one sentence.")
    return ProfileValidation(ok=not warnings, warnings=warnings, suggestions=suggestions)
