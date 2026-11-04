"""API router for learner progress telemetry, streaks, and dashboard aggregates."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models import User
from app.schemas.progress import (
    DashboardProgressResponse,
    ReadinessBreakdown,
    StreakResponse,
)
from app.services import progress_service

router = APIRouter()


@router.get(
    "/dashboard",
    response_model=DashboardProgressResponse,
    summary="Get consolidated telemetry and aggregates for the student dashboard",
)
def get_dashboard_summary(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DashboardProgressResponse:
    """Retrieve all metrics, topic mastery cards, activity timeline, streaks, and next actions."""
    return progress_service.get_dashboard_progress(db=db, user_id=current_user.id)


@router.get(
    "/streak",
    response_model=StreakResponse,
    summary="Get current and longest practice streak telemetry",
)
def get_user_streak(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> StreakResponse:
    """Calculate daily practice streaks based on consecutive calendar day activity."""
    curr, longest, last_date = progress_service.calculate_user_streak(db=db, user_id=current_user.id)
    return StreakResponse(
        current_streak_days=curr,
        longest_streak_days=longest,
        last_active_date=last_date,
    )


@router.get(
    "/readiness",
    response_model=ReadinessBreakdown,
    summary="Get placement readiness index and factor score breakdown",
)
def get_readiness_index(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ReadinessBreakdown:
    """Compute multi-factor preparation index combining resume, practice, jobs, and interviews."""
    target_role = progress_service.get_user_target_role(db, current_user.id)
    topic_cards = progress_service.compute_topic_mastery_cards(db, current_user.id)
    return progress_service.compute_readiness_breakdown(
        db=db,
        user_id=current_user.id,
        target_role=target_role,
        masteries=topic_cards,
    )

