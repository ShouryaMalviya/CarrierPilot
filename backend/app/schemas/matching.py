"""Pydantic schemas for explainable job matching and skill gap analysis."""

from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field

DEFAULT_MATCHING_DISCLAIMER = (
    "This score reflects textual alignment and keyword/skill coverage between your resume "
    "and the job posting. It does not predict interview callbacks or hiring outcomes, "
    "nor guarantee placement."
)


class SkillGapBreakdown(BaseModel):
    """Categorized skill gap analysis identifying matched and missing qualifications."""

    matched_required: List[str] = Field(
        default_factory=list, description="Required skills confirmed or extracted on the resume"
    )
    missing_required: List[str] = Field(
        default_factory=list, description="Required skills not found on the resume"
    )
    matched_preferred: List[str] = Field(
        default_factory=list, description="Preferred skills found on the resume"
    )
    missing_preferred: List[str] = Field(
        default_factory=list, description="Preferred skills not found on the resume"
    )
    additional_skills: List[str] = Field(
        default_factory=list, description="Skills listed on the resume that are not mentioned in the job description"
    )


class MatchScoreBreakdown(BaseModel):
    """Component-level match score breakdown explaining the composite score."""

    required_coverage: float = Field(
        description="Fraction of required skills covered (0.0 to 1.0)",
        ge=0.0,
        le=1.0,
    )
    preferred_coverage: float = Field(
        description="Fraction of preferred skills covered (0.0 to 1.0)",
        ge=0.0,
        le=1.0,
    )
    tfidf_similarity: float = Field(
        description="Cosine similarity between resume text and job description (0.0 to 1.0)",
        ge=0.0,
        le=1.0,
    )
    overall_score: float = Field(
        description="Composite match score on a 0.0 to 100.0 scale",
        ge=0.0,
        le=100.0,
    )


class LexicalMatchResponse(BaseModel):
    """Detailed explainable matching result between a resume and a job posting."""

    model_config = ConfigDict(from_attributes=True)

    resume_id: int = Field(description="Analyzed resume ID")
    job_id: int = Field(description="Target job ID")
    job_title: str = Field(description="Target job title")
    company: Optional[str] = Field(default=None, description="Company name")
    scores: MatchScoreBreakdown = Field(description="Component score breakdown")
    skill_gap: SkillGapBreakdown = Field(description="Categorized skill gap details")
    disclaimer: str = Field(
        default=DEFAULT_MATCHING_DISCLAIMER,
        description="Strict ethical disclaimer regarding textual alignment vs. hiring guarantees",
    )


class BatchMatchItem(BaseModel):
    """Summary match item in ranked batch matching results."""

    job_id: int = Field(description="Target job ID")
    job_title: str = Field(description="Target job title")
    company: Optional[str] = Field(default=None, description="Company name")
    is_synthetic: bool = Field(description="Whether the job is a synthetic demo benchmark")
    overall_score: float = Field(description="Overall match score (0.0 to 100.0)")
    required_coverage: float = Field(description="Required skill coverage (0.0 to 1.0)")
    preferred_coverage: float = Field(description="Preferred skill coverage (0.0 to 1.0)")
    tfidf_similarity: float = Field(description="TF-IDF textual cosine similarity (0.0 to 1.0)")
    missing_required_count: int = Field(description="Number of missing required skills")
    missing_required: List[str] = Field(default_factory=list, description="Missing required skill names")


class BatchMatchResponse(BaseModel):
    """Ranked list of job matches for a specific candidate resume."""

    resume_id: int = Field(description="Candidate resume ID")
    total_jobs_evaluated: int = Field(description="Total number of accessible jobs evaluated")
    matches: List[BatchMatchItem] = Field(description="Job matches ranked by overall score descending")
    disclaimer: str = Field(
        default=DEFAULT_MATCHING_DISCLAIMER,
        description="Strict ethical disclaimer regarding textual alignment vs. hiring guarantees",
    )
