"""CareerPilot AI — FastAPI Application Entry Point."""

import logging
import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.exceptions import HTTPException as FastAPIHTTPException, RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from fastapi.middleware.cors import CORSMiddleware

import app
from app.api.v1 import api_router
from app.api.v1.health import get_health
from app.core.config import get_settings
from app.core.errors import (
    generic_exception_handler,
    http_exception_handler,
    validation_exception_handler,
)

logger = logging.getLogger("careerpilot")
settings = get_settings()


@asynccontextmanager
async def lifespan(application: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan context manager for startup and shutdown procedures."""
    # Ensure upload directory exists outside web root
    try:
        os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
        logger.info("Upload directory confirmed at %s", settings.UPLOAD_DIR)
    except Exception as e:
        logger.warning("Could not initialize upload directory at %s: %s", settings.UPLOAD_DIR, e)

    logger.info(
        "CareerPilot AI backend started. Environment: %s, Debug: %s, AI Provider: %s",
        settings.ENVIRONMENT,
        settings.DEBUG,
        settings.AI_PROVIDER,
    )
    yield
    logger.info("CareerPilot AI backend shutting down.")


def create_application() -> FastAPI:
    """Initialize and configure the FastAPI application instance."""
    application = FastAPI(
        title="CareerPilot AI API",
        description="Personalized Placement Intelligence & Adaptive Interview Coach API",
        version=getattr(app, "__version__", "0.1.0"),
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url=f"{settings.API_V1_STR}/openapi.json",
        lifespan=lifespan,
    )

    # Configure CORS with explicit allowed origins
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Register structured exception handlers
    application.add_exception_handler(FastAPIHTTPException, http_exception_handler)
    application.add_exception_handler(StarletteHTTPException, http_exception_handler)
    application.add_exception_handler(RequestValidationError, validation_exception_handler)
    application.add_exception_handler(Exception, generic_exception_handler)

    # Mount versioned API routes
    application.include_router(api_router, prefix=settings.API_V1_STR)

    # Top-level health check endpoint for standard load balancer probes
    application.add_api_route(
        "/health",
        get_health,
        methods=["GET"],
        tags=["Health"],
        summary="Root health check probe",
    )

    @application.get("/", tags=["Root"], summary="API Root information")
    def root():
        return {
            "name": "CareerPilot AI API",
            "version": getattr(app, "__version__", "0.1.0"),
            "status": "online",
            "docs": "/docs",
            "api_v1": settings.API_V1_STR,
        }

    return application


app = create_application()
