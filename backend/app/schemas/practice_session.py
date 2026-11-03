"""Pydantic schemas for interactive diagnostic practice sessions."""

from datetime import datetime
from typing import List, Literal, Optional
from pydantic import BaseModel, ConfigDict, Field

from app.schemas.question import QuestionPublic

SessionDifficulty = Literal["easy", "medium", "hard", "all"]
SessionStatus = Literal["in_progress", "completed", "abandoned"]


class PracticeSessionCreate(BaseModel):
    """Payload to initiate a new diagnostic practice session."""

    model_config = ConfigDict(extra="forbid")

    topic: Optional[str] = Field("all", max_length=100, description="Target domain, e.g. 'Python', 'SQL', or 'all'")
    difficulty: SessionDifficulty = Field("all", description="Difficulty tier filter: easy, medium, hard, or all")
    question_count: int = Field(5, ge=1, le=20, description="Number of questions in this practice session")
    time_limit_seconds: Optional[int] = Field(None, ge=30, le=7200, description="Optional countdown timer in seconds")


class PracticeSessionSummary(BaseModel):
    """Compact representation of a practice session for list views."""

    model_config = ConfigDict(from_attributes=True)

    session_id: str
    topic: str
    difficulty: str
    total_questions: int
    current_index: int
    status: str
    score: float
    time_limit_seconds: Optional[int] = None
    created_at: datetime
    completed_at: Optional[datetime] = None


class PracticeSessionResponse(BaseModel):
    """Full detail of an active or concluded practice session with questions."""

    model_config = ConfigDict(from_attributes=True)

    session_id: str
    topic: str
    difficulty: str
    total_questions: int
    current_index: int
    status: str
    score: float
    time_limit_seconds: Optional[int] = None
    created_at: datetime
    completed_at: Optional[datetime] = None
    questions: List[QuestionPublic]
    current_question: Optional[QuestionPublic] = None
    progress_percentage: float = 0.0
    has_next: bool = False


class PracticeSessionListResponse(BaseModel):
    """Paginated collection of practice session summaries."""

    items: List[PracticeSessionSummary]
    total: int
    skip: int
    limit: int

