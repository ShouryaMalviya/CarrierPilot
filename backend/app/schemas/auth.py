"""Authentication and user management request/response schemas."""

import re
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field, field_validator

EMAIL_PATTERN = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"


class UserRegister(BaseModel):
    """Registration request payload."""

    email: str = Field(pattern=EMAIL_PATTERN, description="User email address")
    password: str = Field(min_length=8, max_length=128, description="User password (minimum 8 characters)")

    @field_validator("email")
    @classmethod
    def normalize_email(cls, v: str) -> str:
        """Strip whitespace and lowercase email."""
        return v.strip().lower()


class UserLogin(BaseModel):
    """Login request payload."""

    email: str = Field(pattern=EMAIL_PATTERN, description="User email address")
    password: str = Field(min_length=1, description="User password")

    @field_validator("email")
    @classmethod
    def normalize_email(cls, v: str) -> str:
        """Strip whitespace and lowercase email."""
        return v.strip().lower()


class Token(BaseModel):
    """OAuth2 Bearer token response."""

    access_token: str = Field(description="Signed JWT access token")
    token_type: str = Field(default="bearer", description="Token type")
    expires_in: int = Field(description="Token expiration window in seconds")


class UserResponse(BaseModel):
    """User profile metadata response."""

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(description="Unique user ID")
    email: str = Field(description="User email address")
    is_active: bool = Field(description="Whether the account is active")
    is_verified: bool = Field(description="Whether email is verified")
    created_at: datetime = Field(description="Account creation timestamp")
