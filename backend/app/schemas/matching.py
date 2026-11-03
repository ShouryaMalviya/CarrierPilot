"""Pydantic schemas for explainable job matching, hybrid scoring, and skill gap analysis."""

from typing import Dict, List, Optional
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


class MatchedSkillEvidence(BaseModel):
    """Resume evidence citation supporting a matched job qualification."""

    canonical_name: str = Field(description="Canonical skill title")
    category: str = Field(default="general", description="Skill taxonomy category")
    is_required: bool = Field(description="Whether this was a required (True) or preferred (False) qualification")
    evidence_snippet: Optional[str] = Field(default=None, description="Exact sentence/snippet quoted from resume")
    confidence_score: Optional[float] = Field(default=1.0, description="Extraction confidence score (0.0 to 1.0)")
    is_user_confirmed: bool = Field(default=False, description="Whether the user explicitly confirmed this skill")


class LearningRecommendation(BaseModel):
    """Actionable diagnostic recommendation targeting a missing qualification."""

    skill_name: str = Field(description="Target skill name to learn or practice")
    category: str = Field(default="general", description="Taxonomy category")
    priority: str = Field(description="Recommendation priority ('high' for required, 'medium' for preferred)")
    rationale: str = Field(description="Plain-text explanation why this skill was recommended")
    suggested_action: str = Field(description="Concrete action item (practice topic, tutorial, or project)")


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
    semantic_similarity: Optional[float] = Field(
        default=None,
        description="Cosine similarity from semantic embeddings if available (0.0 to 1.0)",
        ge=0.0,
        le=1.0,
    )
    overall_score: float = Field(
        description="Composite match score on a 0.0 to 100.0 scale",
        ge=0.0,
        le=100.0,
    )
    similarity_mode: str = Field(
        default="lexical",
        description="Active similarity method: 'semantic', 'lexical', or 'lexical_fallback'",
    )
    is_fallback: bool = Field(
        default=False,
        description="True if fallback to lexical matching occurred instead of neural embeddings",
    )
    fallback_reason: Optional[str] = Field(
        default=None,
        description="Explanation when fallback mode is active",
    )
    applied_weights: Dict[str, float] = Field(
        default_factory=dict,
        description="Transparent breakdown of weights applied to each scoring component",
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
    evidence: List[MatchedSkillEvidence] = Field(
        default_factory=list, description="Traceable resume citations for matched skills"
    )
    recommendations: List[LearningRecommendation] = Field(
        default_factory=list, description="Actionable recommendations addressing skill gaps"
    )
    explanation_summary: str = Field(
        default="", description="Human-readable synthesis explaining the score"
    )
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
    semantic_similarity: Optional[float] = Field(
        default=None, description="Semantic embedding similarity if computed"
    )
    similarity_mode: str = Field(
        default="lexical", description="Similarity mode ('semantic', 'lexical', or 'lexical_fallback')"
    )
    is_fallback: bool = Field(default=False, description="Whether fallback mode was active")
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


class SemanticStatusResponse(BaseModel):
    """Diagnostic status for the optional semantic similarity provider."""

    is_available: bool = Field(description="Whether a semantic embedding model is loaded and ready")
    model_name: str = Field(description="Configured or active embedding model name")
    provider_type: str = Field(description="Active provider class name")
    fallback_mode: bool = Field(description="Whether the system is currently defaulting to lexical fallback")
    last_error: Optional[str] = Field(default=None, description="Diagnostic error from loading attempt if any")
