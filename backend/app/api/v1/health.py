"""Health check endpoint handler."""

from datetime import datetime, timezone
from fastapi import APIRouter, Depends, status
from app.core.config import Settings, get_settings
from app.schemas.health import HealthResponse, ServicesStatus
import app

router = APIRouter()


@router.get(
    "",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    summary="Check application and service health",
)
def get_health(settings: Settings = Depends(get_settings)) -> HealthResponse:
    """Return lightweight health check status without blocking on external services."""
    # Check if a database URL is configured
    db_status = "configured" if settings.DATABASE_URL else "unconfigured"

    return HealthResponse(
        status="healthy",
        environment=settings.ENVIRONMENT,
        version=getattr(app, "__version__", "0.1.0"),
        timestamp=datetime.now(timezone.utc),
        services=ServicesStatus(
            database=db_status,
            ai_provider=settings.AI_PROVIDER,
            semantic_embeddings=settings.ENABLE_SEMANTIC_EMBEDDINGS,
        ),
    )
