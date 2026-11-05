"""Service layer for typed mock interview sessions and question catalog."""

import json
from pathlib import Path
from typing import List, Optional, Tuple
from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.entities import InterviewSession, Profile, User
from app.schemas.interview import (
    CuratedInterviewQuestion,
    InterviewCatalogResponse,
    InterviewResponseSubmit,
    InterviewSessionCreate,
)
from app.schemas.rubric import RubricFeedback
from app.services import rubric_service

# Location of curated seed questions
SEED_QUESTIONS_PATH = Path(__file__).resolve().parent.parent / "data" / "seed_interview_questions.json"

_QUESTION_CACHE: Optional[List[CuratedInterviewQuestion]] = None


def load_curated_questions(force_reload: bool = False) -> List[CuratedInterviewQuestion]:
    """Load curated mock interview questions from disk with in-memory caching."""
    global _QUESTION_CACHE
    if _QUESTION_CACHE is not None and not force_reload:
        return _QUESTION_CACHE

    if not SEED_QUESTIONS_PATH.exists():
        _QUESTION_CACHE = []
        return _QUESTION_CACHE

    with open(SEED_QUESTIONS_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    questions = [CuratedInterviewQuestion(**item) for item in data]
    _QUESTION_CACHE = questions
    return _QUESTION_CACHE


def get_interview_catalog(
    role: Optional[str] = None,
    competency: Optional[str] = None,
) -> InterviewCatalogResponse:
    """Retrieve catalog of curated questions with optional role and competency filtering."""
    all_questions = load_curated_questions()
    roles = sorted(list(set(q.role for q in all_questions)))
    competencies = sorted(list(set(q.competency for q in all_questions)))

    filtered = all_questions
    if role:
        r_lower = role.strip().lower()
        filtered = [q for q in filtered if q.role.lower() == r_lower]
    if competency:
        c_lower = competency.strip().lower()
        filtered = [q for q in filtered if q.competency.lower() == c_lower]

    return InterviewCatalogResponse(
        total_questions=len(filtered),
        roles=roles,
        competencies=competencies,
        questions=filtered,
    )


def get_curated_question_by_id(question_id: str) -> Optional[CuratedInterviewQuestion]:
    """Retrieve a specific curated question by its identifier."""
    all_questions = load_curated_questions()
    for q in all_questions:
        if q.id == question_id:
            return q
    return None


def create_interview_session(
    db: Session,
    user: User,
    payload: InterviewSessionCreate,
) -> InterviewSession:
    """Initialize a new typed mock interview session."""
    all_questions = load_curated_questions()

    # Determine target role
    target_role = "Full-Stack Engineer"
    if payload.role and payload.role.strip():
        target_role = payload.role.strip()
    else:
        # Check user's profile
        user_profile = db.scalar(select(Profile).where(Profile.user_id == user.id))
        if user_profile and user_profile.target_role:
            target_role = user_profile.target_role

    # Determine competency
    competency = "System Design"
    if payload.competency and payload.competency.strip():
        competency = payload.competency.strip()

    # Determine question prompt
    if payload.custom_question_text and payload.custom_question_text.strip():
        question_text = payload.custom_question_text.strip()
    elif payload.question_id:
        curated_q = get_curated_question_by_id(payload.question_id)
        if not curated_q:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Interview question with ID '{payload.question_id}' not found in curated catalog.",
            )
        question_text = curated_q.question_text
        if not payload.role:
            target_role = curated_q.role
        if not payload.competency:
            competency = curated_q.competency
    else:
        # Find best matching curated question for this role & competency
        matched = [
            q for q in all_questions
            if q.role.lower() == target_role.lower() and q.competency.lower() == competency.lower()
        ]
        if not matched:
            # Fall back to role-only matching
            matched = [q for q in all_questions if q.role.lower() == target_role.lower()]
        if not matched:
            # Fall back to competency-only matching
            matched = [q for q in all_questions if q.competency.lower() == competency.lower()]
        if not matched and all_questions:
            matched = all_questions

        if matched:
            # Pick the first matching question (or could randomize)
            chosen = matched[0]
            question_text = chosen.question_text
            target_role = chosen.role
            competency = chosen.competency
        else:
            question_text = "Describe a challenging technical architectural decision you made and the trade-offs involved."

    session = InterviewSession(
        user_id=user.id,
        role=target_role,
        competency=competency,
        question_text=question_text,
        user_response=None,
        rubric_version="1.0.0",
        total_score=None,
        dimension_scores=None,
        feedback_json=None,
        model_provider="local",
        status="in_progress",
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


def get_interview_session(
    db: Session,
    session_id: int,
    user_id: int,
) -> InterviewSession:
    """Retrieve an interview session with user ownership validation."""
    session = db.scalar(
        select(InterviewSession).where(
            InterviewSession.id == session_id,
            InterviewSession.user_id == user_id,
        )
    )
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Interview session not found.",
        )
    return session


def list_interview_sessions(
    db: Session,
    user_id: int,
    role: Optional[str] = None,
    competency: Optional[str] = None,
    session_status: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
) -> Tuple[int, List[InterviewSession]]:
    """List interview sessions belonging to the user with optional filters."""
    query = select(InterviewSession).where(InterviewSession.user_id == user_id)

    if role:
        query = query.where(func.lower(InterviewSession.role) == role.strip().lower())
    if competency:
        query = query.where(func.lower(InterviewSession.competency) == competency.strip().lower())
    if session_status:
        query = query.where(InterviewSession.status == session_status.strip().lower())

    # Total count query
    count_query = select(func.count()).select_from(query.subquery())
    total = db.scalar(count_query) or 0

    # Paginated results ordered by creation time descending
    records_query = query.order_by(InterviewSession.created_at.desc()).offset(skip).limit(limit)
    sessions = list(db.scalars(records_query).all())

    return total, sessions


def submit_interview_response(
    db: Session,
    session_id: int,
    user_id: int,
    payload: InterviewResponseSubmit,
) -> InterviewSession:
    """Submit a typed response for an interview session and compute rubric coaching feedback."""
    session = get_interview_session(db, session_id=session_id, user_id=user_id)

    if session.status != "in_progress":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot submit response for session in status '{session.status}'. Only in-progress sessions accept answers.",
        )

    clean_text = payload.user_response.strip()
    if len(clean_text) < 20:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Candidate response must be at least 20 non-whitespace characters long.",
        )

    # Determine key concepts from question bank if applicable
    all_questions = load_curated_questions()
    key_concepts: List[str] = []
    for q in all_questions:
        if q.question_text == session.question_text or (q.role == session.role and q.competency == session.competency):
            key_concepts = q.key_concepts
            break

    # Compute deterministic rubric feedback across the 5 dimensions
    feedback = rubric_service.evaluate_response(
        question_text=session.question_text,
        user_response=clean_text,
        role=session.role,
        competency=session.competency,
        key_concepts=key_concepts,
    )

    session.user_response = clean_text
    session.status = "completed"
    session.rubric_version = feedback.rubric_version
    session.total_score = feedback.total_score
    session.dimension_scores = {k: v.model_dump() for k, v in feedback.dimension_scores.items()}
    session.feedback_json = feedback.model_dump()

    db.commit()
    db.refresh(session)
    return session


def get_interview_feedback(
    db: Session,
    session_id: int,
    user_id: int,
) -> RubricFeedback:
    """Retrieve structured rubric coaching feedback for a completed interview session."""
    session = get_interview_session(db, session_id=session_id, user_id=user_id)

    if not session.feedback_json or session.status not in ("submitted", "completed"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Interview session {session_id} has not been completed or evaluated yet.",
        )

    return RubricFeedback(**session.feedback_json)


def abandon_interview_session(
    db: Session,
    session_id: int,
    user_id: int,
) -> InterviewSession:
    """Abandon an in-progress interview session."""
    session = get_interview_session(db, session_id=session_id, user_id=user_id)

    if session.status != "in_progress":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot abandon session with status '{session.status}'. Only in-progress sessions can be abandoned.",
        )

    session.status = "abandoned"
    db.commit()
    db.refresh(session)
    return session

