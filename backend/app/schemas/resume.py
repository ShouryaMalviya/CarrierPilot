"""Pydantic schemas for resume upload and metadata management."""

from datetime import datetime
from typing import List
from pydantic import BaseModel, ConfigDict, Field


class ResumeResponse(BaseModel):
    """Resume metadata record response."""

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(description="Unique resume database record ID")
    user_id: int = Field(description="Owner user ID")
    original_filename: str = Field(description="Sanitized original document filename")
    file_key: str = Field(description="Opaque non-guessable storage identifier")
    file_size_bytes: int = Field(description="Size of the uploaded document in bytes")
    mime_type: str = Field(description="Verified document MIME type")
    parse_status: str = Field(description="Parsing lifecycle status (pending, completed, failed)")
    parser_version: str = Field(description="Parser version tag")
    created_at: datetime = Field(description="Upload timestamp")
    updated_at: datetime = Field(description="Last update timestamp")


class ResumeListResponse(BaseModel):
    """Paginated or listed collection of uploaded resumes for current user."""

    resumes: List[ResumeResponse]
    total: int

