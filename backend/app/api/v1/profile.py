"""User profile management and onboarding routes."""

from typing import List
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models import Profile, User
from app.schemas.profile import (
    DEFAULT_SUPPORTED_ROLES,
    OnboardingDisclosure,
    ProfileResponse,
    ProfileUpdate,
)

router = APIRouter()


@router.get(
    "",
    response_model=ProfileResponse,
    status_code=status.HTTP_200_OK,
    summary="Retrieve current user's profile",
)
def get_my_profile(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ProfileResponse:
    """Fetch the active placement profile scoped strictly to the authenticated user."""
    profile = db.query(Profile).filter(Profile.user_id == current_user.id).first()
    if not profile:
        # Fallback creation if user record existed without associated profile
        profile = Profile(
            user_id=current_user.id,
            target_role="Junior Python Developer",
            preferred_language="English",
            consent_analytics=True,
        )
        db.add(profile)
        db.commit()
        db.refresh(profile)

    return ProfileResponse.model_validate(profile)


@router.put(
    "",
    response_model=ProfileResponse,
    status_code=status.HTTP_200_OK,
    summary="Update current user's profile",
)
def update_my_profile(
    payload: ProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ProfileResponse:
    """Update profile preferences, target role, and consent flags for the authenticated user."""
    profile = db.query(Profile).filter(Profile.user_id == current_user.id).first()
    if not profile:
        profile = Profile(user_id=current_user.id)
        db.add(profile)

    if payload.target_role is not None:
        profile.target_role = payload.target_role.strip()

    if payload.preferred_language is not None:
        profile.preferred_language = payload.preferred_language.strip()

    if payload.consent_analytics is not None:
        profile.consent_analytics = payload.consent_analytics

    db.commit()
    db.refresh(profile)
    return ProfileResponse.model_validate(profile)


@router.get(
    "/roles",
    response_model=List[str],
    status_code=status.HTTP_200_OK,
    summary="List recommended target role presets",
)
def list_target_roles() -> List[str]:
    """Return default curated roles available for selection during onboarding."""
    return DEFAULT_SUPPORTED_ROLES


@router.get(
    "/onboarding-info",
    response_model=OnboardingDisclosure,
    status_code=status.HTTP_200_OK,
    summary="Get onboarding terms, purpose, and disclaimers",
)
def get_onboarding_info() -> OnboardingDisclosure:
    """Return explicit educational boundaries, consent information, and non-hiring disclaimers."""
    return OnboardingDisclosure()

