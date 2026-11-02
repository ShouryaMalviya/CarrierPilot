"""Pydantic schemas for resume upload, extraction, and metadata management."""

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class ResumeResponse(BaseModel):
    """Resume metadata and extracted content record response."""

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(description="Unique resume database record ID")
    user_id: int = Field(description="Owner user ID")
    original_filename: str = Field(description="Sanitized original document filename")
    file_key: str = Field(description="Opaque non-guessable storage identifier")
    file_size_bytes: int = Field(description="Size of the uploaded document in bytes")
    mime_type: str = Field(description="Verified document MIME type")
    parse_status: str = Field(description="Parsing lifecycle status (pending, completed, warning, failed)")
    parser_version: str = Field(description="Parser version tag")
    parsed_content: Optional[Dict[str, Any]] = Field(default=None, description="Extracted content payload and metadata")
    created_at: datetime = Field(description="Upload timestamp")
    updated_at: datetime = Field(description="Last update timestamp")

    @property
    def extracted_text(self) -> Optional[str]:
        """Convenience accessor for extracted plain text."""
        if self.parsed_content and isinstance(self.parsed_content, dict):
            return self.parsed_content.get("text")
        return None

    @property
    def warnings(self) -> List[str]:
        """Convenience accessor for extraction warnings."""
        if self.parsed_content and isinstance(self.parsed_content, dict):
            return self.parsed_content.get("warnings", [])
        return []


class ResumeListResponse(BaseModel):
    """Collection of uploaded resumes for current user."""

    resumes: List[ResumeResponse]
    total: int
