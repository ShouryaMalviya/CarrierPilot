"""API endpoints for typed mock interview sessions and curated question catalog."""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models.entities import User
from app.schemas.interview import (
    CuratedInterviewQuestion,
    InterviewCatalogResponse,
    InterviewResponseSubmit,
    InterviewSessionCreate,
    InterviewSessionListResponse,
    InterviewSessionPublic,
)
from app.services import interview_service

router = APIRouter()


@router.get(
    "/catalog",
    response_model=InterviewCatalogResponse,
    summary="List curated technical and behavioral mock interview questions",
)
def get_interview_catalog(
    role: Optional[str] = Query(None, description="Filter questions by target role"),
    competency: Optional[str] = Query(None, description="Filter questions by competency"),
) -> InterviewCatalogResponse:
    """Retrieve catalog of curated technical interview prompts across domains."""
    return interview_service.get_interview_catalog(role=role, competency=competency)


@router.get(
    "/catalog/{question_id}",
    response_model=CuratedInterviewQuestion,
    summary="Get details of a specific curated interview question",
)
def get_curated_question(question_id: str) -> CuratedInterviewQuestion:
    """Retrieve details, guidelines, and expected key concepts for a question."""
    question = interview_service.get_curated_question_by_id(question_id)
    if not question:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Interview question '{question_id}' not found.",
        )
    return question


@router.post(
    "/sessions",
    response_model=InterviewSessionPublic,
    status_code=status.HTTP_201_CREATED,
    summary="Initiate a new typed mock interview session",
)
def create_session(
    payload: InterviewSessionCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> InterviewSessionPublic:
    """Start a new typed mock interview session with a curated or custom prompt."""
    return interview_service.create_interview_session(db, user=current_user, payload=payload)


@router.get(
    "/sessions",
    response_model=InterviewSessionListResponse,
    summary="List current user's mock interview sessions",
)
def list_sessions(
    role: Optional[str] = Query(None, description="Filter by role"),
    competency: Optional[str] = Query(None, description="Filter by competency"),
    status: Optional[str] = Query(None, description="Filter by status (in_progress, submitted, completed, abandoned)"),
    skip: int = Query(0, ge=0, description="Offset for pagination"),
    limit: int = Query(20, ge=1, le=100, description="Page limit"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> InterviewSessionListResponse:
    """Retrieve paginated list of user's past and active mock interview sessions."""
    total, sessions = interview_service.list_interview_sessions(
        db,
        user_id=current_user.id,
        role=role,
        competency=competency,
        session_status=status,
        skip=skip,
        limit=limit,
    )
    return InterviewSessionListResponse(total=total, sessions=sessions)


@router.get(
    "/sessions/{session_id}",
    response_model=InterviewSessionPublic,
    summary="Get details of a specific interview session",
)
def get_session(
    session_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> InterviewSessionPublic:
    """Retrieve session details, questions, answers, and rubric evaluations."""
    return interview_service.get_interview_session(db, session_id=session_id, user_id=current_user.id)


@router.post(
    "/sessions/{session_id}/submit",
    response_model=InterviewSessionPublic,
    summary="Submit candidate's typed response for an interview session",
)
def submit_response(
    session_id: int,
    payload: InterviewResponseSubmit,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> InterviewSessionPublic:
    """Submit written answer to conclude the interview and queue rubric coaching."""
    return interview_service.submit_interview_response(
        db, session_id=session_id, user_id=current_user.id, payload=payload
    )


@router.post(
    "/sessions/{session_id}/abandon",
    response_model=InterviewSessionPublic,
    summary="Abandon an in-progress interview session",
)
def abandon_session(
    session_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> InterviewSessionPublic:
    """Mark an active session as abandoned."""
    return interview_service.abandon_interview_session(db, session_id=session_id, user_id=current_user.id)
