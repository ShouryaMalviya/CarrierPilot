"""File upload security, MIME verification, magic-byte inspection, and sanitization."""

import io
import os
import re
import zipfile
from typing import Tuple
from fastapi import HTTPException, status
from app.core.config import get_settings

settings = get_settings()

ALLOWED_EXTENSIONS = {".pdf", ".docx"}
PDF_MAGIC_BYTES = b"%PDF-"
DOCX_ZIP_MAGIC_BYTES = b"PK\x03\x04"


def sanitize_filename(filename: str) -> str:
    """Strip path traversal sequences and dangerous characters from user filenames."""
    if not filename:
        return "resume.pdf"
    # Extract only the base name (no directory paths)
    base = os.path.basename(filename)
    # Strip any characters that are not alphanumeric, dash, underscore, dot, or space
    clean = re.sub(r"[^\w\s\.\-]", "", base)
    return clean[:255] if clean else "resume.pdf"


def validate_resume_file(content: bytes, filename: str) -> Tuple[str, str, str]:
    """Inspect and validate uploaded resume file size, extension, and content signatures.

    Returns:
        (sanitized_filename, clean_extension, mime_type)
    """
    # 1. Size bounds validation
    file_size = len(content)
    if file_size == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "EMPTY_FILE",
                "message": "The uploaded file is empty (0 bytes). Please upload a valid document.",
            },
        )

    max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    if file_size > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail={
                "code": "FILE_TOO_LARGE",
                "message": f"Uploaded file ({file_size / (1024*1024):.1f}MB) exceeds maximum limit of {settings.MAX_UPLOAD_SIZE_MB}MB.",
            },
        )

    # 2. Extension validation
    sanitized = sanitize_filename(filename)
    _, ext = os.path.splitext(sanitized)
    clean_ext = ext.lower()

    if clean_ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "UNSUPPORTED_FILE_TYPE",
                "message": f"File extension '{clean_ext}' is not supported. Only PDF (.pdf) and Word (.docx) files are accepted.",
            },
        )

    # 3. Magic-byte signature inspection
    if clean_ext == ".pdf":
        if not content.startswith(PDF_MAGIC_BYTES):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "code": "INVALID_PDF_SIGNATURE",
                    "message": "File does not match the valid PDF binary signature (%PDF-). The file may be corrupt or misnamed.",
                },
            )
        mime_type = "application/pdf"

    elif clean_ext == ".docx":
        if not content.startswith(DOCX_ZIP_MAGIC_BYTES):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "code": "INVALID_DOCX_SIGNATURE",
                    "message": "File does not match the valid DOCX OpenXML archive signature. The file may be corrupt or misnamed.",
                },
            )
        # Verify it can be parsed as a zip and contains word document parts
        try:
            with zipfile.ZipFile(io.BytesIO(content)) as zf:
                namelist = zf.namelist()
                if not any(name.startswith("word/") or name == "[Content_Types].xml" for name in namelist):
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail={
                            "code": "INVALID_DOCX_STRUCTURE",
                            "message": "File is a zip archive but does not contain valid DOCX document XML structures.",
                        },
                    )
        except zipfile.BadZipFile:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "code": "CORRUPT_DOCX_FILE",
                    "message": "The uploaded DOCX archive is corrupt and could not be read.",
                },
            )
        mime_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"

    return sanitized, clean_ext, mime_type
