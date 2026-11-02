"""Job intake, description parsing, requirement management, and demo benchmark routes."""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload

from app.api.deps import get_current_user, get_db
from app.models import Job, JobSkill, Skill, User
from app.schemas.job import JobCreate, JobListResponse, JobResponse, JobSkillResponse, JobUpdate
from app.services.job_parser import parse_job_skills, seed_synthetic_jobs
from app.services.skill_taxonomy import ensure_default_skills, normalize_skill_name

router = APIRouter()


def _attach_skills(
    db: Session, job: Job, required_skills: List[str], preferred_skills: List[str]
) -> None:
    """Normalize and attach required and preferred skills to a job posting."""
    skill_map = ensure_default_skills(db)
    attached_skill_ids = set()

    for s_name in required_skills:
        canonical = normalize_skill_name(s_name)
        skill = skill_map.get(canonical) or db.query(Skill).filter(Skill.canonical_name == canonical).first()
        if not skill:
            skill = Skill(canonical_name=canonical, category="custom", aliases=[s_name])
            db.add(skill)
            db.flush()
            skill_map[canonical] = skill

        if skill.id not in attached_skill_ids:
            attached_skill_ids.add(skill.id)
            db.add(JobSkill(job_id=job.id, skill_id=skill.id, is_required=True))

    for s_name in preferred_skills:
        canonical = normalize_skill_name(s_name)
        skill = skill_map.get(canonical) or db.query(Skill).filter(Skill.canonical_name == canonical).first()
        if not skill:
            skill = Skill(canonical_name=canonical, category="custom", aliases=[s_name])
            db.add(skill)
            db.flush()
            skill_map[canonical] = skill

        if skill.id not in attached_skill_ids:
            attached_skill_ids.add(skill.id)
            db.add(JobSkill(job_id=job.id, skill_id=skill.id, is_required=False))


def format_job_response(job: Job) -> JobResponse:
    """Format an ORM Job entity with nested skills into a clean Pydantic response."""
    skills_list: List[JobSkillResponse] = []
    required_names: List[str] = []
    preferred_names: List[str] = []

    for js in job.job_skills:
        skill = js.skill
        c_name = skill.canonical_name if skill else ""
        cat = skill.category if skill else "custom"
        skills_list.append(
            JobSkillResponse(
                id=js.id,
                skill_id=js.skill_id,
                canonical_name=c_name,
                category=cat,
                is_required=js.is_required,
            )
        )
        if js.is_required:
            required_names.append(c_name)
        else:
            preferred_names.append(c_name)

    return JobResponse(
        id=job.id,
        user_id=job.user_id,
        title=job.title,
        company=job.company,
        description=job.description,
        source_url=job.source_url,
        is_synthetic=job.is_synthetic,
        is_active=job.is_active,
        required_skills=sorted(required_names),
        preferred_skills=sorted(preferred_names),
        skills=skills_list,
        created_at=job.created_at,
        updated_at=job.updated_at,
    )


@router.post(
    "",
    response_model=JobResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new job posting with automatic or explicit skill extraction",
)
def create_job(
    payload: JobCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> JobResponse:
    """Intake a job description, identify required and preferred skills, and persist."""
    job = Job(
        user_id=current_user.id,
        title=payload.title,
        company=payload.company,
        description=payload.description,
        source_url=payload.source_url,
        is_synthetic=False,
        is_active=True,
    )
    db.add(job)
    db.flush()

    if payload.required_skills is not None or payload.preferred_skills is not None:
        req_skills = payload.required_skills or []
        pref_skills = payload.preferred_skills or []
    else:
        req_skills, pref_skills = parse_job_skills(payload.description)

    _attach_skills(db, job, req_skills, pref_skills)
    db.commit()

    # Re-query with eager load for clean return
    loaded_job = (
        db.query(Job)
        .options(joinedload(Job.job_skills).joinedload(JobSkill.skill))
        .filter(Job.id == job.id)
        .first()
    )
    return format_job_response(loaded_job)


@router.get(
    "",
    response_model=JobListResponse,
    status_code=status.HTTP_200_OK,
    summary="List available jobs (user-created and synthetic demo fixtures)",
)
def list_jobs(
    is_synthetic: Optional[bool] = Query(default=None, description="Filter by synthetic status"),
    search: Optional[str] = Query(default=None, description="Search term in title, company, or text"),
    limit: int = Query(default=50, ge=1, le=100, description="Max items to return"),
    offset: int = Query(default=0, ge=0, description="Offset items"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> JobListResponse:
    """Retrieve all jobs accessible to the current user (owned + public synthetic)."""
    query = (
        db.query(Job)
        .options(joinedload(Job.job_skills).joinedload(JobSkill.skill))
        .filter(or_(Job.user_id == current_user.id, Job.is_synthetic == True))  # noqa: E712
    )

    if is_synthetic is not None:
        query = query.filter(Job.is_synthetic == is_synthetic)

    if search:
        pattern = f"%{search}%"
        query = query.filter(
            or_(
                Job.title.ilike(pattern),
                Job.company.ilike(pattern),
                Job.description.ilike(pattern),
            )
        )

    total = query.count()
    jobs = query.order_by(Job.created_at.desc()).offset(offset).limit(limit).all()

    return JobListResponse(
        jobs=[format_job_response(j) for j in jobs],
        total=total,
    )


@router.post(
    "/seed-demo",
    response_model=List[JobResponse],
    status_code=status.HTTP_200_OK,
    summary="Seed or ensure standard synthetic benchmark demo jobs",
)
def seed_demo_jobs(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> List[JobResponse]:
    """Seed idempotent synthetic benchmark jobs for offline testing and demonstration."""
    seeded = seed_synthetic_jobs(db)
    # Re-query seeded jobs with relations
    ids = [j.id for j in seeded]
    loaded = (
        db.query(Job)
        .options(joinedload(Job.job_skills).joinedload(JobSkill.skill))
        .filter(Job.id.in_(ids))
        .all()
    )
    return [format_job_response(j) for j in loaded]


@router.get(
    "/{job_id}",
    response_model=JobResponse,
    status_code=status.HTTP_200_OK,
    summary="Get single job details and skill requirements",
)
def get_job(
    job_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> JobResponse:
    """Retrieve details for a specific job owned by user or marked synthetic."""
    job = (
        db.query(Job)
        .options(joinedload(Job.job_skills).joinedload(JobSkill.skill))
        .filter(Job.id == job_id)
        .first()
    )
    if not job or (job.user_id != current_user.id and not job.is_synthetic):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "JOB_NOT_FOUND", "message": "The requested job was not found."},
        )

    return format_job_response(job)


@router.put(
    "/{job_id}",
    response_model=JobResponse,
    status_code=status.HTTP_200_OK,
    summary="Update an existing user-owned job and refresh skills",
)
def update_job(
    job_id: int,
    payload: JobUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> JobResponse:
    """Update job title, description, or skill requirements. Strictly isolated to owner."""
    job = (
        db.query(Job)
        .options(joinedload(Job.job_skills).joinedload(JobSkill.skill))
        .filter(Job.id == job_id, Job.user_id == current_user.id)
        .first()
    )
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "JOB_NOT_FOUND", "message": "The requested job was not found or cannot be modified."},
        )

    if payload.title is not None:
        job.title = payload.title
    if payload.company is not None:
        job.company = payload.company
    if payload.source_url is not None:
        job.source_url = payload.source_url
    if payload.is_active is not None:
        job.is_active = payload.is_active

    skills_need_update = False
    if payload.required_skills is not None or payload.preferred_skills is not None:
        skills_need_update = True
        req_skills = payload.required_skills if payload.required_skills is not None else [
            js.skill.canonical_name for js in job.job_skills if js.is_required
        ]
        pref_skills = payload.preferred_skills if payload.preferred_skills is not None else [
            js.skill.canonical_name for js in job.job_skills if not js.is_required
        ]
    elif payload.description is not None and payload.description != job.description:
        skills_need_update = True
        job.description = payload.description
        req_skills, pref_skills = parse_job_skills(job.description)
    elif payload.description is not None:
        job.description = payload.description

    if skills_need_update:
        # Clear existing job skills and re-attach
        job.job_skills.clear()
        db.flush()
        _attach_skills(db, job, req_skills, pref_skills)

    db.commit()
    db.refresh(job)
    return format_job_response(job)


@router.delete(
    "/{job_id}",
    status_code=status.HTTP_200_OK,
    summary="Delete a user-owned job posting",
)
def delete_job(
    job_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Delete a user-owned job posting. Synthetic jobs and other users' jobs are protected."""
    job = (
        db.query(Job)
        .filter(Job.id == job_id, Job.user_id == current_user.id)
        .first()
    )
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "JOB_NOT_FOUND", "message": "The requested job was not found or cannot be deleted."},
        )

    db.delete(job)
    db.commit()
    return {"message": f"Job {job_id} deleted successfully."}

