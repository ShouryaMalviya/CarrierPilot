"""Pydantic schemas for job intake, management, and skill requirements."""

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class JobSkillResponse(BaseModel):
    """Job skill association with canonical name and requirement flag."""

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(description="JobSkill link ID")
    skill_id: int = Field(description="Canonical Skill ID")
    canonical_name: str = Field(description="Canonical skill name")
    category: str = Field(description="Skill category")
    is_required: bool = Field(description="Whether this skill is required (True) or preferred (False)")


class JobCreate(BaseModel):
    """Job posting creation payload."""

    title: str = Field(min_length=2, max_length=200, description="Job title")
    company: Optional[str] = Field(default=None, max_length=200, description="Company name")
    description: str = Field(min_length=20, max_length=50000, description="Full job description text")
    source_url: Optional[str] = Field(default=None, max_length=500, description="Origin URL or identifier")
    required_skills: Optional[List[str]] = Field(
        default=None, description="Optional manual override of required skills"
    )
    preferred_skills: Optional[List[str]] = Field(
        default=None, description="Optional manual override of preferred skills"
    )


class JobUpdate(BaseModel):
    """Job posting update payload."""

    title: Optional[str] = Field(default=None, min_length=2, max_length=200, description="Updated job title")
    company: Optional[str] = Field(default=None, max_length=200, description="Updated company name")
    description: Optional[str] = Field(
        default=None, min_length=20, max_length=50000, description="Updated job description text"
    )
    source_url: Optional[str] = Field(default=None, max_length=500, description="Updated source URL")
    required_skills: Optional[List[str]] = Field(default=None, description="Updated required skills list")
    preferred_skills: Optional[List[str]] = Field(default=None, description="Updated preferred skills list")
    is_active: Optional[bool] = Field(default=None, description="Active status")


class JobResponse(BaseModel):
    """Job posting response model."""

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(description="Job ID")
    user_id: Optional[int] = Field(default=None, description="Owner user ID or None for synthetic public jobs")
    title: str = Field(description="Job title")
    company: Optional[str] = Field(default=None, description="Company name")
    description: str = Field(description="Full job description")
    source_url: Optional[str] = Field(default=None, description="Job posting source URL or synthetic key")
    is_synthetic: bool = Field(description="Whether this is a synthetic demo benchmark job")
    is_active: bool = Field(description="Whether the job posting is active")
    required_skills: List[str] = Field(default_factory=list, description="List of required canonical skill names")
    preferred_skills: List[str] = Field(default_factory=list, description="List of preferred canonical skill names")
    skills: List[JobSkillResponse] = Field(default_factory=list, description="Detailed skill links")
    created_at: datetime = Field(description="Creation timestamp")
    updated_at: datetime = Field(description="Last update timestamp")


class JobListResponse(BaseModel):
    """Paginated or complete list of job postings."""

    jobs: List[JobResponse] = Field(description="List of jobs")
    total: int = Field(description="Total count of matching jobs")

