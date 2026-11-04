"""Pydantic schemas for typed mock interview sessions and catalog."""

from datetime import datetime
from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, ConfigDict, Field

INTERVIEW_ETHICAL_DISCLAIMER = (
    "CareerPilot AI mock interview scores evaluate written technical articulation and structured "
    "reasoning against standardized rubrics. They do not predict interview callbacks or hiring outcomes, "
    "nor guarantee placement. The platform does not analyze voice, video, or biometric indicators."
)

InterviewSessionStatus = Literal["in_progress", "submitted", "completed", "abandoned"]


class CuratedInterviewQuestion(BaseModel):
    """Curated technical or behavioral mock interview question from the bank."""

    model_config = ConfigDict(from_attributes=True)

    id: str = Field(..., description="Unique question identifier")
    role: str = Field(..., description="Target role name")
    competency: str = Field(..., description="Interview competency category")
    title: str = Field(..., description="Concise question title")
    question_text: str = Field(..., description="Full prompt presented to the candidate")
    guidelines: str = Field(..., description="Structural guidelines and methodology hints")
    key_concepts: List[str] = Field(default_factory=list, description="Core concepts expected")
    difficulty: str = Field("intermediate", description="Difficulty tier: entry, intermediate, advanced")


class InterviewSessionCreate(BaseModel):
    """Request payload to initiate a new typed mock interview session."""

    model_config = ConfigDict(extra="forbid")

    role: Optional[str] = Field(None, max_length=100, description="Target role (defaults to user's profile target role)")
    competency: Optional[str] = Field(None, max_length=100, description="Competency area (System Design, Coding, etc.)")
    question_id: Optional[str] = Field(None, max_length=100, description="Specific curated question ID to practice")
    custom_question_text: Optional[str] = Field(
        None, min_length=10, max_length=2000, description="Custom technical prompt supplied by the candidate"
    )


class InterviewResponseSubmit(BaseModel):
    """Candidate's typed answer submission for evaluation."""

    model_config = ConfigDict(extra="forbid")

    user_response: str = Field(
        ...,
        min_length=20,
        max_length=10000,
        description="Candidate's comprehensive written response to the interview question",
    )
    duration_seconds: Optional[int] = Field(
        None, ge=0, le=86400, description="Time in seconds taken to draft and submit the response"
    )


class InterviewSessionPublic(BaseModel):
    """Public representation of an interview session, response, and scoring status."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    role: str
    competency: str
    question_text: str
    user_response: Optional[str] = None
    rubric_version: str = "1.0.0"
    total_score: Optional[float] = None
    dimension_scores: Optional[Dict[str, Any]] = None
    feedback_json: Optional[Dict[str, Any]] = None
    model_provider: str = "local"
    status: InterviewSessionStatus = "in_progress"
    disclaimer: str = Field(default=INTERVIEW_ETHICAL_DISCLAIMER)
    created_at: datetime
    updated_at: datetime


class InterviewSessionListResponse(BaseModel):
    """Paginated collection of interview sessions for the current user."""

    total: int = Field(..., ge=0)
    sessions: List[InterviewSessionPublic] = Field(default_factory=list)
    disclaimer: str = Field(default=INTERVIEW_ETHICAL_DISCLAIMER)


class InterviewCatalogResponse(BaseModel):
    """Overview of curated interview questions, roles, and competencies."""

    total_questions: int = Field(..., ge=0)
    roles: List[str] = Field(default_factory=list)
    competencies: List[str] = Field(default_factory=list)
    questions: List[CuratedInterviewQuestion] = Field(default_factory=list)
