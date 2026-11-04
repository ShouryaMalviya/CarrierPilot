"""Pydantic schemas for practice attempt submission, grading feedback, and statistics."""

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class AttemptSubmit(BaseModel):
    """Payload for submitting an answer attempt to a practice question."""

    model_config = ConfigDict(extra="forbid")

    question_id: int = Field(..., gt=0, description="Target question ID")
    user_answer: str = Field(..., min_length=1, max_length=10, description="Selected option ID, e.g. 'A', 'B', 'C', 'D'")
    duration_seconds: Optional[int] = Field(None, ge=0, le=7200, description="Time taken to answer in seconds")
    session_id: Optional[str] = Field(None, max_length=64, description="Optional associated practice session ID")


class AttemptFeedback(BaseModel):
    """Immediate post-submission grading feedback revealing answer key and explanation."""

    model_config = ConfigDict(from_attributes=True)

    attempt_id: int
    question_id: int
    session_id: Optional[str] = None
    user_answer: str
    is_correct: bool
    score: float = Field(..., ge=0.0, le=1.0, description="Score awarded: 1.0 for correct, 0.0 for incorrect")
    correct_answer_key: str = Field(..., description="The correct option ID, now revealed post-attempt")
    explanation: str = Field(..., description="Educational explanation of why the answer is correct")
    duration_seconds: Optional[int] = None
    grading_version: str = "1.0.0"
    created_at: datetime


class AttemptHistoryItem(BaseModel):
    """Historical practice attempt record with question context."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    question_id: int
    session_id: Optional[str] = None
    topic: str
    difficulty: str
    prompt: str
    user_answer: str
    correct_answer_key: str
    is_correct: bool
    score: float
    duration_seconds: Optional[int] = None
    created_at: datetime


class AttemptListResponse(BaseModel):
    """Paginated collection of historical attempts."""

    items: List[AttemptHistoryItem]
    total: int
    skip: int
    limit: int


class TopicStat(BaseModel):
    """Summary of attempts within a single topic."""

    total_attempts: int
    correct_attempts: int
    accuracy_percentage: float


class AttemptStatsSummary(BaseModel):
    """Aggregate statistics of user practice activity."""

    total_attempts: int
    correct_attempts: int
    accuracy_percentage: float
    total_time_seconds: int
    by_topic: Dict[str, TopicStat]
    by_difficulty: Dict[str, TopicStat]
