"""Structured error handling and standard error response schemas."""

import logging
from typing import Any, List, Optional, Union
from fastapi import Request, status
from fastapi.exceptions import HTTPException as FastAPIHTTPException, RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

logger = logging.getLogger("careerpilot.errors")


class ErrorDetail(BaseModel):
    """Normalized error detail envelope."""

    code: str = Field(description="Machine-readable error code")
    message: str = Field(description="Human-readable explanation of the error")
    details: Optional[List[Any]] = Field(default=None, description="Detailed validation errors or context")


class ErrorResponse(BaseModel):
    """Standardized API error response body."""

    error: ErrorDetail


async def http_exception_handler(
    request: Request,
    exc: Union[FastAPIHTTPException, StarletteHTTPException],
) -> JSONResponse:
    """Format HTTPExceptions into the standard error envelope."""
    error_code = "HTTP_ERROR"
    if exc.status_code == status.HTTP_404_NOT_FOUND:
        error_code = "RESOURCE_NOT_FOUND"
    elif exc.status_code == status.HTTP_401_UNAUTHORIZED:
        error_code = "UNAUTHORIZED"
    elif exc.status_code == status.HTTP_403_FORBIDDEN:
        error_code = "FORBIDDEN"
    elif exc.status_code == status.HTTP_400_BAD_REQUEST:
        error_code = "BAD_REQUEST"

    # In case detail is already a dict with code/message
    if isinstance(exc.detail, dict):
        message = exc.detail.get("message", "An error occurred")
        error_code = exc.detail.get("code", error_code)
        details = exc.detail.get("details", None)
    else:
        message = str(exc.detail) if exc.detail else "An error occurred"
        details = None

    payload = ErrorResponse(
        error=ErrorDetail(
            code=error_code,
            message=message,
            details=details,
        )
    ).model_dump()

    return JSONResponse(
        status_code=exc.status_code,
        content=payload,
        headers=getattr(exc, "headers", None),
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Format Pydantic RequestValidationErrors into the standard envelope."""
    clean_errors = []
    for err in exc.errors():
        clean_err = {
            "type": err.get("type"),
            "loc": [str(x) for x in err.get("loc", [])],
            "msg": err.get("msg"),
        }
        clean_errors.append(clean_err)

    payload = ErrorResponse(
        error=ErrorDetail(
            code="VALIDATION_ERROR",
            message="Request validation failed. Please check the supplied parameters.",
            details=clean_errors,
        )
    ).model_dump()

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=payload,
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle uncaught exceptions safely without leaking internal stack traces or secrets."""
    logger.exception("Unhandled server exception processing request to %s: %s", request.url.path, exc)

    payload = ErrorResponse(
        error=ErrorDetail(
            code="INTERNAL_SERVER_ERROR",
            message="An unexpected server error occurred. Please try again later.",
            details=None,
        )
    ).model_dump()

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=payload,
    )
