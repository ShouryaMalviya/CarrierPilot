"""API v1 router registry."""

from fastapi import APIRouter
from app.api.v1.auth import router as auth_router
from app.api.v1.health import router as health_router
from app.api.v1.jobs import router as jobs_router
from app.api.v1.matching import router as matching_router
from app.api.v1.practice import router as practice_router
from app.api.v1.profile import router as profile_router
from app.api.v1.progress import router as progress_router
from app.api.v1.resume import router as resume_router

api_router = APIRouter()
api_router.include_router(health_router, prefix="/health", tags=["Health"])
api_router.include_router(auth_router, prefix="/auth", tags=["Authentication"])
api_router.include_router(profile_router, prefix="/profile", tags=["Profile"])
api_router.include_router(resume_router, prefix="/resumes", tags=["Resumes"])
api_router.include_router(jobs_router, prefix="/jobs", tags=["Jobs"])
api_router.include_router(matching_router, prefix="/matching", tags=["Matching"])
api_router.include_router(practice_router, prefix="/practice", tags=["Practice"])
api_router.include_router(progress_router, prefix="/progress", tags=["Progress"])
