"""Application settings and environment configuration module.

Validates environment variables safely using Pydantic Settings.
Non-critical AI credentials and ML model flags remain optional,
ensuring core application functionality boots without third-party keys.
"""

from functools import lru_cache
from typing import List, Optional, Union
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuration settings for CareerPilot AI backend."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # Runtime & Server
    ENVIRONMENT: str = Field(default="development", description="Current runtime environment (development, test, production)")
    DEBUG: bool = Field(default=True, description="Enable debug mode and verbose logging")
    PORT: int = Field(default=8000, description="Port on which the FastAPI application runs")
    HOST: str = Field(default="127.0.0.1", description="Host address to bind to")
    API_V1_STR: str = Field(default="/api/v1", description="API version 1 route prefix")

    # Security & Authentication
    SECRET_KEY: str = Field(
        default="development-insecure-secret-key-min-32-chars-long",
        min_length=16,
        description="Secret key used for signing JWT tokens. Must be securely overridden in production.",
    )
    ALGORITHM: str = Field(default="HS256", description="JWT signing algorithm")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(
        default=60,
        gt=0,
        description="JWT token validity lifetime in minutes",
    )

    # Database
    DATABASE_URL: str = Field(
        default="sqlite:///./careerpilot.db",
        description="Database connection URL. Defaults to local SQLite for test/development.",
    )

    # CORS
    CORS_ORIGINS: Union[List[str], str] = Field(
        default=["http://localhost:5173", "http://127.0.0.1:5173"],
        description="Allowed CORS origins for web client.",
    )

    # File Storage
    UPLOAD_DIR: str = Field(
        default="./uploads/resumes",
        description="Local directory for storing uploaded resume files outside the web root.",
    )
    MAX_UPLOAD_SIZE_MB: int = Field(
        default=5,
        gt=0,
        le=50,
        description="Maximum permitted resume upload size in megabytes.",
    )

    # Optional AI Provider (Deterministic Local Fallback by default)
    AI_PROVIDER: str = Field(
        default="local",
        description="Active AI provider: 'local' (deterministic fallback), 'openai', 'anthropic', 'gemini'.",
    )
    AI_API_KEY: Optional[str] = Field(
        default=None,
        description="Optional API key for external LLM provider. When omitted, system defaults to deterministic rubric coaching.",
    )
    AI_MODEL: str = Field(
        default="gpt-4o-mini",
        description="Target model identifier when using an external LLM provider.",
    )
    AI_REQUEST_TIMEOUT_SECONDS: int = Field(
        default=15,
        gt=0,
        le=60,
        description="Network timeout for external AI requests.",
    )

    # Optional Semantic Matching
    ENABLE_SEMANTIC_EMBEDDINGS: bool = Field(
        default=False,
        description="Whether to attempt loading sentence transformer models. When false, uses scikit-learn TF-IDF baseline.",
    )
    EMBEDDING_MODEL: str = Field(
        default="all-MiniLM-L6-v2",
        description="HuggingFace sentence-transformers model name or local path.",
    )

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        """Parse comma-separated origin strings into a cleaned list of origin URLs."""
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        elif isinstance(v, list):
            return [origin.strip() for origin in v if isinstance(origin, str) and origin.strip()]
        return ["http://localhost:5173", "http://127.0.0.1:5173"]

    @field_validator("ENVIRONMENT")
    @classmethod
    def validate_environment(cls, v: str) -> str:
        """Validate environment string."""
        allowed = {"development", "test", "staging", "production"}
        v_clean = v.strip().lower()
        if v_clean not in allowed:
            raise ValueError(f"ENVIRONMENT must be one of {allowed}, got '{v}'")
        return v_clean


@lru_cache
def get_settings() -> Settings:
    """Return a cached instance of validated application settings."""
    return Settings()

