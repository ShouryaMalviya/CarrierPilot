"""Pydantic schemas for user profile and onboarding workflows."""

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field

DEFAULT_SUPPORTED_ROLES = [
    "Junior Python Developer",
    "Entry-Level Data/ML Analyst",
    "Associate Frontend Developer",
]


class ProfileUpdate(BaseModel):
    """User profile update request payload."""

    target_role: Optional[str] = Field(
        default=None,
        min_length=2,
        max_length=100,
        description="Target job title for tailored placement preparation",
    )
    preferred_language: Optional[str] = Field(
        default=None,
        min_length=2,
        max_length=50,
        description="Preferred user interface and communication language",
    )
    consent_analytics: Optional[bool] = Field(
        default=None,
        description="User consent for tracking aggregate placement preparation metrics",
    )


class ProfileResponse(BaseModel):
    """Profile data transfer model."""

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(description="Unique profile record ID")
    user_id: int = Field(description="Associated user account ID")
    target_role: str = Field(description="Target job role")
    preferred_language: str = Field(description="User language preference")
    consent_analytics: bool = Field(description="Analytics consent status")
    created_at: datetime = Field(description="Creation timestamp")
    updated_at: datetime = Field(description="Last update timestamp")


class OnboardingDisclosure(BaseModel):
    """Clear educational purpose, consent terms, and non-hiring disclaimers."""

    purpose: str = Field(
        description="Educational and coaching purpose of CareerPilot AI",
        default="CareerPilot AI provides evidence-backed placement preparation, diagnostic practice, and interview coaching.",
    )
    disclaimers: List[str] = Field(
        description="Product boundaries and non-goals",
        default=[
            "CareerPilot AI is an educational coaching tool, not an employment agency or recruiter.",
            "Matching scores indicate curriculum alignment and keyword coverage; they are not hiring probabilities.",
            "CareerPilot AI does not predict hiring decisions, nor does it guarantee employment or placement.",
        ],
    )
    data_retention_policy: str = Field(
        description="Summary of user data control and retention",
        default="Your resume and practice history are stored securely and privately. You retain full control to edit or delete your data at any time.",
    )
    camera_or_mic_required: bool = Field(
        default=False,
        description="Camera and microphone are strictly optional; all core mock interview features operate via typed responses.",
    )
    supported_roles: List[str] = Field(
        default=DEFAULT_SUPPORTED_ROLES,
        description="Curated target role presets available during onboarding",
    )
