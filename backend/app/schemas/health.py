"""Health check response schemas."""

from datetime import datetime
from pydantic import BaseModel, Field


class ServicesStatus(BaseModel):
    """Component service availability states."""

    database: str = Field(description="Database configuration or connectivity status")
    ai_provider: str = Field(description="Configured AI provider adapter mode ('local', 'openai', etc.)")
    semantic_embeddings: bool = Field(description="Whether optional semantic embeddings are enabled")


class HealthResponse(BaseModel):
    """Application health endpoint response payload."""

    status: str = Field(default="healthy", description="Application overall health status")
    environment: str = Field(description="Runtime environment")
    version: str = Field(description="Application version")
    timestamp: datetime = Field(description="UTC timestamp of the health check")
    services: ServicesStatus
