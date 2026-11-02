"""Pydantic schemas for resume section parsing, skill extraction, and user corrections."""

from datetime import datetime
from typing import Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class ExtractedSkillResponse(BaseModel):
    """Extracted skill data transfer model."""

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(description="ResumeSkill database record ID")
    resume_id: int = Field(description="Associated resume ID")
    skill_id: int = Field(description="Canonical Skill ID")
    canonical_name: str = Field(description="Normalized canonical skill name")
    category: str = Field(description="Skill category (languages, frameworks, databases, tools)")
    evidence_snippet: Optional[str] = Field(default=None, description="Exact sentence/snippet where skill was mentioned")
    confidence_score: Optional[float] = Field(default=1.0, description="Extraction confidence score (0.0 to 1.0)")
    is_user_confirmed: bool = Field(description="Whether the skill has been explicitly confirmed by user")
    is_auto_extracted: bool = Field(description="Whether the skill was automatically extracted by parser")
    created_at: datetime = Field(description="Creation timestamp")


class AddSkillRequest(BaseModel):
    """User request to add a missing skill to a resume."""

    skill_name: str = Field(min_length=1, max_length=100, description="Name or alias of the skill to attach")
    evidence_snippet: Optional[str] = Field(default="User added", description="Optional manual evidence note")


class UpdateSkillRequest(BaseModel):
    """User request to confirm or modify an extracted skill."""

    is_user_confirmed: Optional[bool] = Field(default=None, description="Mark as confirmed or unconfirmed")
    evidence_snippet: Optional[str] = Field(default=None, description="Updated evidence citation")


class ResumeSectionsResponse(BaseModel):
    """Segmented sections and associated extracted skills for a resume."""

    resume_id: int = Field(description="Resume ID")
    sections: Dict[str, str] = Field(description="Segmented text blocks (skills, experience, projects, education)")
    skills: List[ExtractedSkillResponse] = Field(description="Extracted and confirmed skills list")


class UpdateSectionsRequest(BaseModel):
    """User correction request to edit segmented section contents."""

    sections: Dict[str, str] = Field(description="Dictionary of updated section texts")

