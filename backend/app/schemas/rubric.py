"""Pydantic schemas for 5-dimension mock interview rubric evaluation and coaching feedback."""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.interview import INTERVIEW_ETHICAL_DISCLAIMER


class DimensionScore(BaseModel):
    """Evaluation score and specific feedback for one rubric dimension."""

    model_config = ConfigDict(from_attributes=True)

    dimension: str = Field(..., description="Dimension key (e.g. relevance, technical_correctness)")
    label: str = Field(..., description="Display title (e.g. 'Relevance to Prompt')")
    score: float = Field(..., ge=0.0, le=20.0, description="Awarded score bounded between 0.0 and 20.0")
    max_score: float = Field(20.0, description="Maximum possible points for this dimension")
    feedback: str = Field(..., description="Qualitative evaluation and coaching feedback")
    positive_evidence: List[str] = Field(
        default_factory=list, description="Verbatim quote snippets from the candidate's answer"
    )

    @field_validator("score", mode="before")
    @classmethod
    def clamp_dimension_score(cls, v: Any) -> float:
        """Ensure score is always strictly clamped between 0.0 and 20.0."""
        try:
            val = float(v)
            return round(max(0.0, min(20.0, val)), 1)
        except (ValueError, TypeError):
            return 0.0


class RubricFeedback(BaseModel):
    """Complete structured coaching evaluation across all 5 dimensions."""

    model_config = ConfigDict(from_attributes=True)

    rubric_version: str = Field("1.0.0", description="Semantic version of the evaluation rubric")
    total_score: float = Field(..., ge=0.0, le=100.0, description="Composite score (0.0 - 100.0)")
    dimension_scores: Dict[str, DimensionScore] = Field(
        ...,
        description="Detailed breakdown by dimension (relevance, technical_correctness, completeness, structure, use_of_examples)",
    )
    key_concepts_covered: List[str] = Field(
        default_factory=list, description="Expected concepts successfully identified in response"
    )
    key_concepts_missed: List[str] = Field(
        default_factory=list, description="Expected core concepts absent from response"
    )
    positive_highlights: List[str] = Field(
        default_factory=list, description="Key candidate strengths with cited quotes"
    )
    actionable_improvements: List[str] = Field(
        default_factory=list, description="Concrete remediation advice to elevate response quality"
    )
    summary: str = Field(..., description="Overall executive summary of performance")
    disclaimer: str = Field(
        default=INTERVIEW_ETHICAL_DISCLAIMER,
        description="Mandatory ethical disclaimer regarding scores and lack of biometric inference",
    )

    @field_validator("total_score", mode="before")
    @classmethod
    def clamp_total_score(cls, v: Any) -> float:
        """Ensure total score is always strictly clamped between 0.0 and 100.0."""
        try:
            val = float(v)
            return round(max(0.0, min(100.0, val)), 1)
        except (ValueError, TypeError):
            return 0.0
