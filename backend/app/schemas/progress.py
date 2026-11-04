"""Pydantic schemas for learner progress, streaks, telemetry, and dashboard aggregates."""

from datetime import datetime
from typing import List, Literal, Optional
from pydantic import BaseModel, ConfigDict, Field

from app.schemas.matching import DEFAULT_MATCHING_DISCLAIMER

StatusTier = Literal["proficient", "developing", "needs_practice", "unattempted"]
ActionType = Literal[
    "upload_resume",
    "start_practice",
    "remediate_weak_topic",
    "advance_challenge",
    "mock_interview",
    "explore_jobs",
]
ReadinessTier = Literal["beginner", "developing", "placement_ready", "interview_ready"]


class DailyActivity(BaseModel):
    """Daily practice telemetry volume for trend charting."""

    date: str = Field(description="ISO date string, e.g. '2026-11-04'")
    attempt_count: int = Field(0, ge=0)
    correct_count: int = Field(0, ge=0)
    duration_seconds: int = Field(0, ge=0)


class DashboardTopicMastery(BaseModel):
    """Topic mastery status bar summary formatted for dashboard visualizations."""

    topic: str
    mastery_score: float = Field(..., ge=0.0, le=100.0)
    recent_attempts_count: int = Field(..., ge=0)
    accuracy_percentage: float = Field(..., ge=0.0, le=100.0)
    status_tier: StatusTier
    reason_codes: List[str] = Field(default_factory=list)


class NextRecommendedAction(BaseModel):
    """Primary high-impact action card displayed on the student dashboard."""

    action_type: ActionType
    title: str
    description: str
    target_topic: Optional[str] = None
    target_url: Optional[str] = None


class ReadinessBreakdown(BaseModel):
    """Composite placement preparation index with component factor scores."""

    overall_readiness_score: float = Field(..., ge=0.0, le=100.0)
    profile_resume_score: float = Field(..., ge=0.0, le=100.0)
    practice_mastery_score: float = Field(..., ge=0.0, le=100.0)
    job_matching_score: float = Field(..., ge=0.0, le=100.0)
    mock_interview_score: float = Field(..., ge=0.0, le=100.0)
    readiness_level: ReadinessTier
    disclaimer: str = Field(default=DEFAULT_MATCHING_DISCLAIMER)


class StreakResponse(BaseModel):
    """Practice streak telemetry."""

    current_streak_days: int = Field(..., ge=0)
    longest_streak_days: int = Field(..., ge=0)
    last_active_date: Optional[str] = None


class DashboardProgressResponse(BaseModel):
    """Consolidated telemetry and progress aggregate for the learner dashboard."""

    model_config = ConfigDict(from_attributes=True)

    user_id: int
    target_role: str
    readiness: ReadinessBreakdown
    streak_days: int
    longest_streak_days: int
    total_attempts: int
    correct_attempts: int
    overall_accuracy_percentage: float
    total_practice_time_seconds: int
    completed_sessions_count: int
    active_sessions_count: int
    topic_masteries: List[DashboardTopicMastery]
    activity_timeline: List[DailyActivity]
    next_action: NextRecommendedAction
    generated_at: datetime
