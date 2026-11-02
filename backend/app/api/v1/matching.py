"""Explainable lexical job matching and skill gap analysis routes."""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload

from app.api.deps import get_current_user, get_db
from app.models import Job, JobSkill, Resume, ResumeSkill, Skill, User
from app.schemas.matching import BatchMatchResponse, LexicalMatchResponse
from app.services.matching_service import match_resume_to_all_jobs, match_resume_to_job

router = APIRouter()


@router.post(
    "/resumes/{resume_id}/jobs/{job_id}",
    response_model=LexicalMatchResponse,
    status_code=status.HTTP_200_OK,
    summary="Compute explainable lexical match between a resume and a specific job posting",
)
def match_resume_with_job(
    resume_id: int,
    job_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> LexicalMatchResponse:
    """Evaluate candidate resume against a job posting with TF-IDF similarity and skill gap analysis."""
    # 1. Fetch resume belonging strictly to current user
    resume = (
        db.query(Resume)
        .options(joinedload(Resume.resume_skills).joinedload(ResumeSkill.skill))
        .filter(Resume.id == resume_id, Resume.user_id == current_user.id)
        .first()
    )
    if not resume:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "RESUME_NOT_FOUND", "message": "The requested resume was not found."},
        )

    # 2. Fetch job (must belong to user or be a public synthetic demo job)
    job = (
        db.query(Job)
        .options(joinedload(Job.job_skills).joinedload(JobSkill.skill))
        .filter(Job.id == job_id)
        .first()
    )
    if not job or (job.user_id != current_user.id and not job.is_synthetic):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "JOB_NOT_FOUND", "message": "The requested job posting was not found."},
        )

    return match_resume_to_job(resume, job)


@router.post(
    "/resumes/{resume_id}/batch",
    response_model=BatchMatchResponse,
    status_code=status.HTTP_200_OK,
    summary="Evaluate candidate resume across all accessible jobs and rank matches",
)
def batch_match_resume(
    resume_id: int,
    limit: int = Query(default=50, ge=1, le=100, description="Max matches to return"),
    offset: int = Query(default=0, ge=0, description="Offset for pagination"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> BatchMatchResponse:
    """Rank all accessible jobs against the candidate resume with transparent scores."""
    # 1. Verify resume ownership
    resume = (
        db.query(Resume)
        .options(joinedload(Resume.resume_skills).joinedload(ResumeSkill.skill))
        .filter(Resume.id == resume_id, Resume.user_id == current_user.id)
        .first()
    )
    if not resume:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "RESUME_NOT_FOUND", "message": "The requested resume was not found."},
        )

    # 2. Query accessible active jobs (owned + synthetic)
    accessible_jobs = (
        db.query(Job)
        .options(joinedload(Job.job_skills).joinedload(JobSkill.skill))
        .filter(
            or_(Job.user_id == current_user.id, Job.is_synthetic == True),  # noqa: E712
            Job.is_active == True,  # noqa: E712
        )
        .all()
    )

    return match_resume_to_all_jobs(
        db=db,
        resume=resume,
        accessible_jobs=accessible_jobs,
        limit=limit,
        offset=offset,
    )
