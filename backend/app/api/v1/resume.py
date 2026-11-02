"""Resume upload, storage, text extraction, and lifecycle management routes."""

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models import Resume, User
from app.schemas.resume import ResumeListResponse, ResumeResponse
from app.services.file_validation import validate_resume_file
from app.services.storage import storage_service
from app.services.text_extraction import extract_text_from_file

router = APIRouter()


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
    """Upload, validate, privately store, and extract text from a resume document."""
    # 1. Read file contents safely
    try:
        content = file.file.read()
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "UPLOAD_READ_ERROR", "message": "Failed to read uploaded file payload."},
        )

    # 2. Validate file extension, magic-byte signatures, and size
    clean_filename, clean_ext, mime_type = validate_resume_file(content, file.filename or "resume.pdf")

    # 3. Save to private filesystem storage with non-guessable opaque key
    file_key, file_path = storage_service.save_file(content, clean_ext)

    # 4. Perform deterministic text extraction
    extraction = extract_text_from_file(file_path, clean_ext)

    # 5. Persist database record scoped to current user
    new_resume = Resume(
        user_id=current_user.id,
        original_filename=clean_filename,
        file_key=file_key,
        file_path=file_path,
        file_size_bytes=len(content),
        mime_type=mime_type,
        parse_status=extraction.status,
        parser_version=extraction.parser_version,
        parsed_content=extraction.to_dict(),
    )
    db.add(new_resume)
    db.commit()
    db.refresh(new_resume)

    return ResumeResponse.model_validate(new_resume)


@router.post(
    "/{resume_id}/extract",
    response_model=ResumeResponse,
    status_code=status.HTTP_200_OK,
    summary="Re-run text extraction on an existing resume",
)
def trigger_extraction(
    resume_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ResumeResponse:
    """Re-run deterministic text extraction on a previously uploaded resume."""
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

    # Determine extension from filename or path
    ext = resume.original_filename.split(".")[-1]
    extraction = extract_text_from_file(resume.file_path, ext)

    resume.parse_status = extraction.status
    resume.parser_version = extraction.parser_version
    resume.parsed_content = extraction.to_dict()

    db.commit()
    db.refresh(resume)

    return ResumeResponse.model_validate(resume)


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

    # Safely remove physical file from disk
    storage_service.delete_file(resume.file_path)

    # Remove database record (cascading to resume_skills)
    db.delete(resume)
    db.commit()

    return {"message": "Resume deleted successfully."}
