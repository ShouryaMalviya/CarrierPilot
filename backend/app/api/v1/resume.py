"""Resume upload, storage, text extraction, section segmentation, and skill correction routes."""

from typing import List
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models import Resume, ResumeSkill, Skill, User
from app.schemas.resume import ResumeListResponse, ResumeResponse
from app.schemas.resume_section import (
    AddSkillRequest,
    ExtractedSkillResponse,
    ResumeSectionsResponse,
    UpdateSectionsRequest,
    UpdateSkillRequest,
)
from app.services.file_validation import validate_resume_file
from app.services.section_parser import extract_skills_with_evidence, segment_resume_sections
from app.services.skill_taxonomy import ensure_default_skills, normalize_skill_name
from app.services.storage import storage_service
from app.services.text_extraction import extract_text_from_file

router = APIRouter()


def _populate_resume_skills(db: Session, resume: Resume, extracted_text: str, sections: dict) -> None:
    """Parse skills from text and create ResumeSkill records for the resume."""
    skill_map = ensure_default_skills(db)
    detected_skills = extract_skills_with_evidence(extracted_text, sections)

    for item in detected_skills:
        canonical_name = item["canonical_name"]
        skill_record = skill_map.get(canonical_name)
        if not skill_record:
            continue

        # Prevent duplicate link insertion
        existing = (
            db.query(ResumeSkill)
            .filter(ResumeSkill.resume_id == resume.id, ResumeSkill.skill_id == skill_record.id)
            .first()
        )
        if not existing:
            new_link = ResumeSkill(
                resume_id=resume.id,
                skill_id=skill_record.id,
                evidence_snippet=item["evidence_snippet"],
                confidence_score=item["confidence_score"],
                is_auto_extracted=True,
                is_user_confirmed=False,
            )
            db.add(new_link)


@router.post(
    "/upload",
    response_model=ResumeResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload and automatically extract text from a PDF or DOCX resume",
)
def upload_resume(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ResumeResponse:
    """Upload, validate, privately store, extract text, and segment sections with skill links."""
    try:
        content = file.file.read()
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "UPLOAD_READ_ERROR", "message": "Failed to read uploaded file payload."},
        )

    clean_filename, clean_ext, mime_type = validate_resume_file(content, file.filename or "resume.pdf")
    file_key, file_path = storage_service.save_file(content, clean_ext)

    extraction = extract_text_from_file(file_path, clean_ext)
    sections = segment_resume_sections(extraction.text)

    parsed_payload = extraction.to_dict()
    parsed_payload["sections"] = sections

    new_resume = Resume(
        user_id=current_user.id,
        original_filename=clean_filename,
        file_key=file_key,
        file_path=file_path,
        file_size_bytes=len(content),
        mime_type=mime_type,
        parse_status=extraction.status,
        parser_version=extraction.parser_version,
        parsed_content=parsed_payload,
    )
    db.add(new_resume)
    db.flush()

    if extraction.text:
        _populate_resume_skills(db, new_resume, extraction.text, sections)

    db.commit()
    db.refresh(new_resume)

    return ResumeResponse.model_validate(new_resume)


@router.post(
    "/{resume_id}/extract",
    response_model=ResumeResponse,
    status_code=status.HTTP_200_OK,
    summary="Re-run text extraction and skill parsing on an existing resume",
)
def trigger_extraction(
    resume_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ResumeResponse:
    """Re-run deterministic text extraction and section parsing on a previously uploaded resume."""
    resume = (
        db.query(Resume)
        .filter(Resume.id == resume_id, Resume.user_id == current_user.id)
        .first()
    )
    if not resume:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "RESUME_NOT_FOUND", "message": "The requested resume was not found."},
        )

    ext = resume.original_filename.split(".")[-1]
    extraction = extract_text_from_file(resume.file_path, ext)
    sections = segment_resume_sections(extraction.text)

    parsed_payload = extraction.to_dict()
    parsed_payload["sections"] = sections

    resume.parse_status = extraction.status
    resume.parser_version = extraction.parser_version
    resume.parsed_content = parsed_payload

    if extraction.text:
        _populate_resume_skills(db, resume, extraction.text, sections)

    db.commit()
    db.refresh(resume)

    return ResumeResponse.model_validate(resume)


@router.get(
    "/{resume_id}/sections",
    response_model=ResumeSectionsResponse,
    status_code=status.HTTP_200_OK,
    summary="Get segmented sections and identified skills with evidence",
)
def get_resume_sections(
    resume_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ResumeSectionsResponse:
    """Return parsed sections and linked skills for user review and editing."""
    resume = (
        db.query(Resume)
        .filter(Resume.id == resume_id, Resume.user_id == current_user.id)
        .first()
    )
    if not resume:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "RESUME_NOT_FOUND", "message": "The requested resume was not found."},
        )

    sections = {}
    if resume.parsed_content and isinstance(resume.parsed_content, dict):
        sections = resume.parsed_content.get("sections", {})

    # Fetch associated skills
    skills_query = (
        db.query(ResumeSkill, Skill)
        .join(Skill, ResumeSkill.skill_id == Skill.id)
        .filter(ResumeSkill.resume_id == resume.id)
        .all()
    )

    skill_responses = []
    for rs, s in skills_query:
        skill_responses.append(
            ExtractedSkillResponse(
                id=rs.id,
                resume_id=rs.resume_id,
                skill_id=s.id,
                canonical_name=s.canonical_name,
                category=s.category,
                evidence_snippet=rs.evidence_snippet,
                confidence_score=rs.confidence_score,
                is_user_confirmed=rs.is_user_confirmed,
                is_auto_extracted=rs.is_auto_extracted,
                created_at=rs.created_at,
            )
        )

    return ResumeSectionsResponse(
        resume_id=resume.id,
        sections=sections,
        skills=skill_responses,
    )


@router.put(
    "/{resume_id}/sections",
    response_model=ResumeSectionsResponse,
    status_code=status.HTTP_200_OK,
    summary="Update segmented resume section texts",
)
def update_resume_sections(
    resume_id: int,
    payload: UpdateSectionsRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ResumeSectionsResponse:
    """Save user edits to parsed resume sections."""
    resume = (
        db.query(Resume)
        .filter(Resume.id == resume_id, Resume.user_id == current_user.id)
        .first()
    )
    if not resume:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "RESUME_NOT_FOUND", "message": "The requested resume was not found."},
        )

    if not resume.parsed_content or not isinstance(resume.parsed_content, dict):
        resume.parsed_content = {}

    current_parsed = dict(resume.parsed_content)
    current_parsed["sections"] = payload.sections
    resume.parsed_content = current_parsed

    db.commit()
    db.refresh(resume)

    return get_resume_sections(resume_id, current_user, db)


@router.get(
    "/{resume_id}/skills",
    response_model=List[ExtractedSkillResponse],
    status_code=status.HTTP_200_OK,
    summary="List extracted and confirmed skills for a resume",
)
def list_resume_skills(
    resume_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> List[ExtractedSkillResponse]:
    """Retrieve all candidate and confirmed skills attached to the user's resume."""
    resume = (
        db.query(Resume)
        .filter(Resume.id == resume_id, Resume.user_id == current_user.id)
        .first()
    )
    if not resume:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "RESUME_NOT_FOUND", "message": "The requested resume was not found."},
        )

    skills_query = (
        db.query(ResumeSkill, Skill)
        .join(Skill, ResumeSkill.skill_id == Skill.id)
        .filter(ResumeSkill.resume_id == resume.id)
        .all()
    )

    return [
        ExtractedSkillResponse(
            id=rs.id,
            resume_id=rs.resume_id,
            skill_id=s.id,
            canonical_name=s.canonical_name,
            category=s.category,
            evidence_snippet=rs.evidence_snippet,
            confidence_score=rs.confidence_score,
            is_user_confirmed=rs.is_user_confirmed,
            is_auto_extracted=rs.is_auto_extracted,
            created_at=rs.created_at,
        )
        for rs, s in skills_query
    ]


@router.post(
    "/{resume_id}/skills",
    response_model=ExtractedSkillResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add a missing skill to a resume",
)
def add_resume_skill(
    resume_id: int,
    payload: AddSkillRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ExtractedSkillResponse:
    """User correction: manually attach a verified skill to their resume."""
    resume = (
        db.query(Resume)
        .filter(Resume.id == resume_id, Resume.user_id == current_user.id)
        .first()
    )
    if not resume:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "RESUME_NOT_FOUND", "message": "The requested resume was not found."},
        )

    canonical_name = normalize_skill_name(payload.skill_name)
    skill = db.query(Skill).filter(Skill.canonical_name == canonical_name).first()
    if not skill:
        skill = Skill(canonical_name=canonical_name, category="custom", aliases=[payload.skill_name])
        db.add(skill)
        db.flush()

    # Check if already linked
    existing_link = (
        db.query(ResumeSkill)
        .filter(ResumeSkill.resume_id == resume.id, ResumeSkill.skill_id == skill.id)
        .first()
    )
    if existing_link:
        existing_link.is_user_confirmed = True
        existing_link.evidence_snippet = payload.evidence_snippet or existing_link.evidence_snippet
        db.commit()
        db.refresh(existing_link)
        target_link = existing_link
    else:
        new_link = ResumeSkill(
            resume_id=resume.id,
            skill_id=skill.id,
            evidence_snippet=payload.evidence_snippet or "User added",
            confidence_score=1.0,
            is_user_confirmed=True,
            is_auto_extracted=False,
        )
        db.add(new_link)
        db.commit()
        db.refresh(new_link)
        target_link = new_link

    return ExtractedSkillResponse(
        id=target_link.id,
        resume_id=target_link.resume_id,
        skill_id=skill.id,
        canonical_name=skill.canonical_name,
        category=skill.category,
        evidence_snippet=target_link.evidence_snippet,
        confidence_score=target_link.confidence_score,
        is_user_confirmed=target_link.is_user_confirmed,
        is_auto_extracted=target_link.is_auto_extracted,
        created_at=target_link.created_at,
    )


@router.put(
    "/{resume_id}/skills/{resume_skill_id}",
    response_model=ExtractedSkillResponse,
    status_code=status.HTTP_200_OK,
    summary="Confirm or edit an extracted skill",
)
def update_resume_skill(
    resume_id: int,
    resume_skill_id: int,
    payload: UpdateSkillRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ExtractedSkillResponse:
    """User confirmation or correction of an extracted candidate skill."""
    resume = (
        db.query(Resume)
        .filter(Resume.id == resume_id, Resume.user_id == current_user.id)
        .first()
    )
    if not resume:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "RESUME_NOT_FOUND", "message": "The requested resume was not found."},
        )

    link = (
        db.query(ResumeSkill)
        .filter(ResumeSkill.id == resume_skill_id, ResumeSkill.resume_id == resume.id)
        .first()
    )
    if not link:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "SKILL_LINK_NOT_FOUND", "message": "The specified skill link was not found."},
        )

    if payload.is_user_confirmed is not None:
        link.is_user_confirmed = payload.is_user_confirmed
    if payload.evidence_snippet is not None:
        link.evidence_snippet = payload.evidence_snippet

    db.commit()
    db.refresh(link)

    skill = db.query(Skill).filter(Skill.id == link.skill_id).first()
    return ExtractedSkillResponse(
        id=link.id,
        resume_id=link.resume_id,
        skill_id=skill.id,
        canonical_name=skill.canonical_name,
        category=skill.category,
        evidence_snippet=link.evidence_snippet,
        confidence_score=link.confidence_score,
        is_user_confirmed=link.is_user_confirmed,
        is_auto_extracted=link.is_auto_extracted,
        created_at=link.created_at,
    )


@router.delete(
    "/{resume_id}/skills/{resume_skill_id}",
    status_code=status.HTTP_200_OK,
    summary="Remove an incorrect or false-positive skill from a resume",
)
def remove_resume_skill(
    resume_id: int,
    resume_skill_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """User correction: delete a false-positive skill from the resume."""
    resume = (
        db.query(Resume)
        .filter(Resume.id == resume_id, Resume.user_id == current_user.id)
        .first()
    )
    if not resume:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "RESUME_NOT_FOUND", "message": "The requested resume was not found."},
        )

    link = (
        db.query(ResumeSkill)
        .filter(ResumeSkill.id == resume_skill_id, ResumeSkill.resume_id == resume.id)
        .first()
    )
    if not link:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "SKILL_LINK_NOT_FOUND", "message": "The specified skill link was not found."},
        )

    db.delete(link)
    db.commit()

    return {"message": "Skill removed from resume."}


@router.get(
    "",
    response_model=ResumeListResponse,
    status_code=status.HTTP_200_OK,
    summary="List all resumes uploaded by current user",
)
def list_my_resumes(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ResumeListResponse:
    """Retrieve all uploaded resume records belonging strictly to the authenticated user."""
    resumes = (
        db.query(Resume)
        .filter(Resume.user_id == current_user.id)
        .order_by(Resume.created_at.desc())
        .all()
    )
    return ResumeListResponse(
        resumes=[ResumeResponse.model_validate(r) for r in resumes],
        total=len(resumes),
    )


@router.get(
    "/{resume_id}",
    response_model=ResumeResponse,
    status_code=status.HTTP_200_OK,
    summary="Retrieve resume metadata and extracted content by ID",
)
def get_resume(
    resume_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ResumeResponse:
    """Fetch a single resume record enforcing strict ownership."""
    resume = (
        db.query(Resume)
        .filter(Resume.id == resume_id, Resume.user_id == current_user.id)
        .first()
    )
    if not resume:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "RESUME_NOT_FOUND", "message": "The requested resume was not found."},
        )

    return ResumeResponse.model_validate(resume)


@router.delete(
    "/{resume_id}",
    status_code=status.HTTP_200_OK,
    summary="Delete a resume and its physical file",
)
def delete_resume(
    resume_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Delete a resume database record and securely remove the file from private storage."""
    resume = (
        db.query(Resume)
        .filter(Resume.id == resume_id, Resume.user_id == current_user.id)
        .first()
    )
    if not resume:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "RESUME_NOT_FOUND", "message": "The requested resume was not found."},
        )

    storage_service.delete_file(resume.file_path)
    db.delete(resume)
    db.commit()

    return {"message": "Resume deleted successfully."}
