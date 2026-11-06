"""Pydantic schemas for transparent topic mastery estimation and audit explanations."""

from datetime import datetime
from typing import Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field, computed_field


class TopicMasteryOut(BaseModel):
    """Transparent topic mastery estimate with explainable reason codes."""

    model_config = ConfigDict(from_attributes=True)

    topic: str
    mastery_score: float = Field(..., ge=0.0, le=100.0, description="Recent-weighted mastery score bounded [0, 100]")
    recent_attempts_count: int = Field(..., ge=0, description="Total attempts analyzed for this topic")
    reason_codes: List[str] = Field(default_factory=list, description="Machine-readable transparent explanation codes")
    last_calculated_at: datetime
    decay_factor: float = Field(0.85, description="Exponential recency decay parameter gamma")
    difficulty_weights: Dict[str, float] = Field(
        default_factory=lambda: {"easy": 0.8, "medium": 1.0, "hard": 1.2},
        description="Difficulty scaling factors",
    )


class TopicMasteryListResponse(BaseModel):
    """Collection of topic masteries for the active user with summary aggregates."""

    items: List[TopicMasteryOut]
    overall_average_mastery: float = Field(..., ge=0.0, le=100.0)
    proficient_topics_count: int = Field(..., ge=0, description="Topics with mastery >= 75%")
    needs_practice_topics_count: int = Field(..., ge=0, description="Topics with mastery < 60%")


class AttemptWeightContribution(BaseModel):
    """Audit breakdown of a single attempt's contribution to the mastery score."""

    attempt_id: int
    question_id: int
    difficulty: str
    is_correct: bool
    recency_index: int
    weight: float
    difficulty_factor: float
    weighted_score: float
    max_possible_weighted_score: float

    @computed_field
    @property
    def attempt_index(self) -> int:
        return self.recency_index + 1

    @computed_field
    @property
    def recency_weight(self) -> float:
        return self.weight

    @computed_field
    @property
    def difficulty_multiplier(self) -> float:
        return self.difficulty_factor

    @computed_field
    @property
    def score_contribution(self) -> float:
        return self.weighted_score


class MasteryCalculationExplanation(BaseModel):
    """Full step-by-step mathematical audit for a topic mastery calculation."""

    topic: str
    mastery_score: float
    total_attempts: int
    decay_gamma: float = 0.85
    formula: str = "Mastery = (sum(w_i * c_i * d_i) / sum(w_i * d_i)) * 100"
    numerator_sum: float
    denominator_sum: float
    reason_codes: List[str]
    attempt_contributions: List[AttemptWeightContribution]
    last_calculated_at: datetime

    @computed_field
    @property
    def decay_factor(self) -> float:
        return self.decay_gamma

    @computed_field
    @property
    def attempts_considered(self) -> int:
        return self.total_attempts

    @computed_field
    @property
    def formula_explanation(self) -> str:
        return self.formula

    @computed_field
    @property
    def contributions(self) -> List[AttemptWeightContribution]:
        return self.attempt_contributions

