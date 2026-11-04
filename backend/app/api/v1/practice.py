"""API router for diagnostic practice questions and topic taxonomy."""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models import User
from app.schemas.practice_attempt import (
    AttemptFeedback,
    AttemptHistoryItem,
    AttemptListResponse,
    AttemptStatsSummary,
    AttemptSubmit,
)
from app.schemas.practice_session import (
    PracticeSessionCreate,
    PracticeSessionListResponse,
    PracticeSessionResponse,
    PracticeSessionSummary,
)
from app.schemas.question import (
    QuestionCreate,
    QuestionDetail,
    QuestionListResponse,
    QuestionPublic,
    QuestionSeedResponse,
    TopicSummary,
)
from app.services import (
    practice_attempt_service,
    practice_session_service,
    question_service,
)

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


# ==============================================================================
# Diagnostic Practice Session Lifecycle Endpoints
# ==============================================================================

@router.post(
    "/sessions",
    response_model=PracticeSessionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new diagnostic practice session",
)
def create_practice_session(
    session_in: PracticeSessionCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PracticeSessionResponse:
    """Initiate a diagnostic session tailored by topic and difficulty."""
    session = practice_session_service.create_practice_session(
        db=db,
        user_id=current_user.id,
        req=session_in,
    )
    return practice_session_service.build_session_response(db, session)


@router.get(
    "/sessions",
    response_model=PracticeSessionListResponse,
    summary="List active and completed practice sessions for the current user",
)
def list_practice_sessions(
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by status (in_progress, completed, abandoned)"),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=50),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PracticeSessionListResponse:
    """Retrieve practice sessions belonging exclusively to the authenticated user."""
    sessions, total = practice_session_service.list_user_sessions(
        db=db,
        user_id=current_user.id,
        status_filter=status_filter,
        skip=skip,
        limit=limit,
    )
    items = [PracticeSessionSummary.model_validate(s) for s in sessions]
    return PracticeSessionListResponse(
        items=items,
        total=total,
        skip=skip,
        limit=limit,
    )


@router.get(
    "/sessions/{session_id}",
    response_model=PracticeSessionResponse,
    summary="Get active practice session status and current question",
)
def get_practice_session(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PracticeSessionResponse:
    """Fetch session state, current question, and progress for the authenticated user."""
    session = practice_session_service.get_practice_session(
        db=db,
        session_id=session_id,
        user_id=current_user.id,
    )
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Practice session '{session_id}' not found.",
        )
    return practice_session_service.build_session_response(db, session)


@router.post(
    "/sessions/{session_id}/next",
    response_model=PracticeSessionResponse,
    summary="Advance to the next question in the practice session",
)
def advance_practice_session(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PracticeSessionResponse:
    """Advance current_index by one, completing session if all questions are finished."""
    session = practice_session_service.get_practice_session(
        db=db,
        session_id=session_id,
        user_id=current_user.id,
    )
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Practice session '{session_id}' not found.",
        )
    if session.status != "in_progress":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot advance session with status '{session.status}'.",
        )
    updated_session = practice_session_service.advance_session(db, session)
    return practice_session_service.build_session_response(db, updated_session)


@router.post(
    "/sessions/{session_id}/abandon",
    response_model=PracticeSessionResponse,
    summary="Abandon an in-progress practice session",
)
def abandon_practice_session(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PracticeSessionResponse:
    """Mark session as abandoned, terminating active question progression."""
    session = practice_session_service.get_practice_session(
        db=db,
        session_id=session_id,
        user_id=current_user.id,
    )
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Practice session '{session_id}' not found.",
        )
    abandoned_session = practice_session_service.abandon_session(db, session)
    return practice_session_service.build_session_response(db, abandoned_session)


# ==============================================================================
# Practice Attempt Submission & History Endpoints
# ==============================================================================

@router.post(
    "/attempts",
    response_model=AttemptFeedback,
    status_code=status.HTTP_201_CREATED,
    summary="Submit and objectively grade a practice question attempt",
)
def submit_practice_attempt(
    submit_in: AttemptSubmit,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AttemptFeedback:
    """Grade an answer attempt deterministically, immediately returning educational feedback."""
    try:
        attempt, question = practice_attempt_service.grade_and_record_attempt(
            db=db,
            user_id=current_user.id,
            submit_in=submit_in,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )

    return AttemptFeedback(
        attempt_id=attempt.id,
        question_id=attempt.question_id,
        session_id=attempt.session_id,
        user_answer=attempt.user_answer,
        is_correct=attempt.is_correct,
        score=attempt.score,
        correct_answer_key=question.answer_key,
        explanation=question.explanation,
        duration_seconds=attempt.duration_seconds,
        grading_version=attempt.grading_version,
        created_at=attempt.created_at,
    )


@router.get(
    "/attempts",
    response_model=AttemptListResponse,
    summary="List historical practice attempts for the current user",
)
def list_practice_attempts(
    topic: Optional[str] = Query(None, description="Filter attempts by question topic domain"),
    session_id: Optional[str] = Query(None, description="Filter attempts by practice session ID"),
    is_correct: Optional[bool] = Query(None, description="Filter by correctness (true or false)"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AttemptListResponse:
    """Retrieve historical attempts with question context and user answer details."""
    items, total = practice_attempt_service.get_user_attempts(
        db=db,
        user_id=current_user.id,
        topic=topic,
        session_id=session_id,
        is_correct=is_correct,
        skip=skip,
        limit=limit,
    )
    return AttemptListResponse(
        items=items,
        total=total,
        skip=skip,
        limit=limit,
    )


@router.get(
    "/attempts/stats",
    response_model=AttemptStatsSummary,
    summary="Get user practice attempt statistics and accuracy metrics",
)
def get_practice_attempt_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AttemptStatsSummary:
    """Compute aggregate accuracy, count, and duration statistics by topic and difficulty."""
    return practice_attempt_service.get_user_attempt_stats(db=db, user_id=current_user.id)


