"""Service layer for diagnostic practice sessions and question delivery."""

from datetime import datetime, timezone
import uuid
from typing import List, Optional, Tuple
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import PracticeSession, Question
from app.schemas.practice_session import (
    PracticeSessionCreate,
    PracticeSessionResponse,
    PracticeSessionSummary,
)
from app.schemas.question import QuestionPublic
from app.services.question_service import seed_questions


def create_practice_session(
    db: Session,
    user_id: int,
    req: PracticeSessionCreate,
) -> PracticeSession:
    """Create a new diagnostic practice session with a tailored question set."""
    # Ensure question bank is seeded if empty
    total_bank_questions = db.scalar(select(func.count(Question.id))) or 0
    if total_bank_questions == 0:
        seed_questions(db)

    # Build question selection query
    query = select(Question.id).where(Question.is_active.is_(True))

    topic_filter = req.topic.strip() if req.topic and req.topic.strip().lower() != "all" else None
    if topic_filter:
        query = query.where(Question.topic == topic_filter)

    diff_filter = req.difficulty.strip().lower() if req.difficulty and req.difficulty != "all" else None
    if diff_filter:
        query = query.where(Question.difficulty == diff_filter)

    matched_ids = list(db.scalars(query.order_by(Question.id.asc())).all())

    # Fallback 1: If difficulty filter was too restrictive, relax difficulty within topic
    if len(matched_ids) < req.question_count and topic_filter and diff_filter:
        fallback_query = select(Question.id).where(
            Question.is_active.is_(True),
            Question.topic == topic_filter,
        )
        matched_ids = list(db.scalars(fallback_query.order_by(Question.id.asc())).all())

    # Fallback 2: If still insufficient, take any active questions across topics
    if len(matched_ids) < req.question_count:
        fallback_all = select(Question.id).where(Question.is_active.is_(True))
        matched_ids = list(db.scalars(fallback_all.order_by(Question.id.asc())).all())

    # Truncate to requested question count
    selected_ids = matched_ids[: req.question_count]
    if not selected_ids:
        # Ultimate fallback: return empty list
        selected_ids = []

    session_id = f"ps_{uuid.uuid4().hex[:16]}"
    session = PracticeSession(
        session_id=session_id,
        user_id=user_id,
        topic=req.topic or "all",
        difficulty=req.difficulty,
        total_questions=len(selected_ids),
        question_ids=selected_ids,
        current_index=0,
        status="in_progress",
        score=0.0,
        time_limit_seconds=req.time_limit_seconds,
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


def get_practice_session(
    db: Session,
    session_id: str,
    user_id: Optional[int] = None,
) -> Optional[PracticeSession]:
    """Retrieve practice session by ID, optionally verifying user ownership."""
    query = select(PracticeSession).where(PracticeSession.session_id == session_id)
    if user_id is not None:
        query = query.where(PracticeSession.user_id == user_id)
    return db.scalar(query)


def build_session_response(
    db: Session,
    session: PracticeSession,
) -> PracticeSessionResponse:
    """Format session into response model with public question payloads."""
    # Fetch questions in the order defined by session.question_ids
    if not session.question_ids:
        questions: List[Question] = []
    else:
        q_map = {
            q.id: q
            for q in db.scalars(select(Question).where(Question.id.in_(session.question_ids))).all()
        }
        questions = [q_map[qid] for qid in session.question_ids if qid in q_map]

    public_questions = [QuestionPublic.model_validate(q) for q in questions]

    current_question: Optional[QuestionPublic] = None
    if (
        session.status == "in_progress"
        and 0 <= session.current_index < len(public_questions)
    ):
        current_question = public_questions[session.current_index]

    total_q = session.total_questions
    current_idx = min(session.current_index, total_q)
    progress_pct = round((current_idx / total_q) * 100.0, 1) if total_q > 0 else 0.0
    has_next = (session.current_index + 1) < total_q and session.status == "in_progress"

    return PracticeSessionResponse(
        session_id=session.session_id,
        topic=session.topic,
        difficulty=session.difficulty,
        total_questions=session.total_questions,
        current_index=session.current_index,
        status=session.status,
        score=session.score,
        time_limit_seconds=session.time_limit_seconds,
        created_at=session.created_at,
        completed_at=session.completed_at,
        questions=public_questions,
        current_question=current_question,
        progress_percentage=progress_pct,
        has_next=has_next,
    )


def advance_session(db: Session, session: PracticeSession) -> PracticeSession:
    """Advance session to the next question or complete it if at the end."""
    if session.status != "in_progress":
        return session

    session.current_index += 1
    if session.current_index >= session.total_questions:
        session.status = "completed"
        session.completed_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(session)
    return session


def abandon_session(db: Session, session: PracticeSession) -> PracticeSession:
    """Mark an in-progress session as abandoned."""
    if session.status == "in_progress":
        session.status = "abandoned"
        session.completed_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(session)
    return session


def list_user_sessions(
    db: Session,
    user_id: int,
    status_filter: Optional[str] = None,
    skip: int = 0,
    limit: int = 20,
) -> Tuple[List[PracticeSession], int]:
    """Retrieve paginated practice sessions for a specific user."""
    query = select(PracticeSession).where(PracticeSession.user_id == user_id)
    count_query = select(func.count(PracticeSession.id)).where(PracticeSession.user_id == user_id)

    if status_filter:
        query = query.where(PracticeSession.status == status_filter.strip().lower())
        count_query = count_query.where(PracticeSession.status == status_filter.strip().lower())

    total = db.scalar(count_query) or 0
    sessions = db.scalars(
        query.order_by(PracticeSession.created_at.desc()).offset(skip).limit(limit)
    ).all()

    return list(sessions), total
