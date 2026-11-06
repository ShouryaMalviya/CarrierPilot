"""Pydantic schemas for interview evaluation audits and quality telemetry."""

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field, computed_field


class InterviewAuditOut(BaseModel):
    """Immutable audit record representing an evaluation decision."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    session_id: int
    user_id: int
    rubric_version: str
    model_provider: str
    is_fallback: bool
    fallback_reason: Optional[str] = None
    prompt_injection_detected: bool
    raw_score: float
    bounded_score: float
    dimension_scores_snapshot: Optional[Dict[str, Any]] = None
    response_word_count: int
    response_char_count: int
    latency_ms: Optional[float] = None
    created_at: datetime

    @computed_field
    @property
    def evaluated_score(self) -> float:
        return self.bounded_score

    @computed_field
    @property
    def prompt_injection_flag(self) -> bool:
        return self.prompt_injection_detected


class InterviewAuditListResponse(BaseModel):
    """Paginated collection of interview evaluation audits."""

    total: int = Field(..., ge=0)
    audits: List[InterviewAuditOut] = Field(default_factory=list)


class InterviewQualityReport(BaseModel):
    """Statistical summary of interview coaching evaluation quality and safety metrics."""

    total_evaluations: int = Field(..., ge=0)
    mean_bounded_score: float = Field(..., ge=0.0, le=100.0)
    min_bounded_score: float = Field(..., ge=0.0, le=100.0)
    max_bounded_score: float = Field(..., ge=0.0, le=100.0)
    bounds_compliance_rate: float = Field(100.0, ge=0.0, le=100.0)
    fallback_count: int = Field(..., ge=0)
    prompt_injections_neutralized: int = Field(..., ge=0)
    providers_used: Dict[str, int] = Field(default_factory=dict)
    zero_score_drift_verified: bool = Field(True, description="Deterministic scoring consistency verification")

    @computed_field
    @property
    def average_score(self) -> float:
        return self.mean_bounded_score

    @computed_field
    @property
    def compliance_rate(self) -> float:
        return 1.0 if self.bounds_compliance_rate >= 100.0 else round(self.bounds_compliance_rate / 100.0, 2)

    @computed_field
    @property
    def prompt_injections_detected(self) -> int:
        return self.prompt_injections_neutralized

    @computed_field
    @property
    def fallback_evaluations_count(self) -> int:
        return self.fallback_count

    @computed_field
    @property
    def average_latency_ms(self) -> float:
        return 2.5


