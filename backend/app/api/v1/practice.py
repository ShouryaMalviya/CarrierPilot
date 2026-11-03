"""API router for diagnostic practice questions and topic taxonomy."""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models import User
from app.schemas.question import (
    QuestionCreate,
    QuestionDetail,
    QuestionListResponse,
    QuestionPublic,
    QuestionSeedResponse,
    TopicSummary,
)
from app.services import question_service

router = APIRouter()


@router.post(
    "/seed",
    response_model=QuestionSeedResponse,
    summary="Seed curated technical questions into the question bank",
)
def seed_curated_questions(
    force_reset: bool = Query(False, description="Whether to clear and re-seed synthetic questions"),
    db: Session = Depends(get_db),
) -> QuestionSeedResponse:
    """Idempotently seed the question bank with curated benchmark MCQs."""
    seeded, total = question_service.seed_questions(db, force_reset=force_reset)
    return QuestionSeedResponse(
        seeded_count=seeded,
        total_count=total,
        message=f"Successfully seeded {seeded} questions. Total questions in bank: {total}.",
    )


@router.get(
    "/topics",
    response_model=List[TopicSummary],
    summary="List available practice topics and question counts",
)
def list_practice_topics(
    db: Session = Depends(get_db),
) -> List[TopicSummary]:
    """Retrieve available topic domains with count breakdown by difficulty level."""
    # Ensure seed questions exist if the bank is completely empty
    summaries = question_service.get_topic_summaries(db)
    if not summaries:
        question_service.seed_questions(db)
        summaries = question_service.get_topic_summaries(db)
    return summaries


@router.get(
    "/questions",
    response_model=QuestionListResponse,
    summary="List active practice questions (public delivery without answers)",
)
def list_practice_questions(
    topic: Optional[str] = Query(None, description="Filter by topic domain (e.g., 'Python', 'SQL')"),
    difficulty: Optional[str] = Query(None, description="Filter by difficulty ('easy', 'medium', 'hard')"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
) -> QuestionListResponse:
    """Retrieve public questions for practice without leaking answer keys or explanations."""
    # Ensure bank is initialized if empty
    questions, total = question_service.list_questions(
        db, topic=topic, difficulty=difficulty, is_active=True, skip=skip, limit=limit
    )
    if total == 0 and topic is None and difficulty is None:
        question_service.seed_questions(db)
        questions, total = question_service.list_questions(
            db, topic=topic, difficulty=difficulty, is_active=True, skip=skip, limit=limit
        )

    public_items = [QuestionPublic.model_validate(q) for q in questions]
    return QuestionListResponse(
        items=public_items,
        total=total,
        skip=skip,
        limit=limit,
    )


@router.get(
    "/questions/{question_id}",
    response_model=QuestionPublic,
    summary="Get a single practice question by ID (public view)",
)
def get_practice_question(
    question_id: int,
    db: Session = Depends(get_db),
) -> QuestionPublic:
    """Get question prompt and options by ID for active attempt solving."""
    question = question_service.get_question(db, question_id)
    if not question or not question.is_active:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Question with ID {question_id} not found.",
        )
    return QuestionPublic.model_validate(question)


@router.get(
    "/questions/{question_id}/detail",
    response_model=QuestionDetail,
    summary="Get question detail including answer key (authenticated inspection)",
)
def get_practice_question_detail(
    question_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> QuestionDetail:
    """Retrieve full question details including answer key and educational explanation."""
    question = question_service.get_question(db, question_id)
    if not question:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Question with ID {question_id} not found.",
        )
    return QuestionDetail.model_validate(question)


@router.post(
    "/questions",
    response_model=QuestionDetail,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new practice question (authenticated)",
)
def create_practice_question(
    question_in: QuestionCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> QuestionDetail:
    """Author a new question with validated options and answer key."""
    question = question_service.create_question(db, question_in)
    return QuestionDetail.model_validate(question)
