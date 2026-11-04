"""Pydantic schemas for adaptive next-question recommendation and structured study plans."""

from datetime import datetime
from typing import List, Literal, Optional
from pydantic import BaseModel, ConfigDict, Field

from app.schemas.question import QuestionPublic

RecommendationPriority = Literal["high", "medium", "low"]
PlanPriorityTier = Literal["immediate_remediation", "consolidation", "maintenance"]


class NextQuestionRecommendation(BaseModel):
    """Adaptive recommendation for the next practice question."""

    model_config = ConfigDict(from_attributes=True)

    question: QuestionPublic
    reason_code: str = Field(description="Machine-readable decision code, e.g. WEAK_TOPIC_REMEDIATION")
    rationale: str = Field(description="Transparent, human-readable justification for the recommendation")
    priority_level: RecommendationPriority = Field(description="Urgency of practicing this item")
    topic_mastery_score: float = Field(..., ge=0.0, le=100.0, description="Current mastery score in this topic")
    target_role: Optional[str] = Field(None, description="User's target job role used to prioritize curriculum")


class StudyPlanTopicItem(BaseModel):
    """A single topic element in a prioritized diagnostic study plan."""

    model_config = ConfigDict(from_attributes=True)

    topic: str
    priority_tier: PlanPriorityTier
    current_mastery: float = Field(..., ge=0.0, le=100.0)
    recent_attempts_count: int
    recommended_questions_count: int = Field(..., ge=1, le=20)
    suggested_difficulty: str = Field("medium", description="Recommended difficulty tier: easy, medium, or hard")
    reason_code: str
    action_items: List[str] = Field(default_factory=list)


class StudyPlanResponse(BaseModel):
    """Personalized diagnostic study roadmap structured by prioritized topic tiers."""

    model_config = ConfigDict(from_attributes=True)

    user_id: int
    target_role: str
    overall_average_mastery: float = Field(..., ge=0.0, le=100.0)
    summary: str
    topics: List[StudyPlanTopicItem]
    generated_at: datetime


class RecommendationAuditOut(BaseModel):
    """Audit log entry capturing recommendation reasoning and target identifier."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    recommendation_type: str
    target_id: Optional[str] = None
    rationale: str
    reason_code: str
    created_at: datetime

