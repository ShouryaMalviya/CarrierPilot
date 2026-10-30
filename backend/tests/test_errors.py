"""Tests for structured API exception handlers and error envelopes."""

import pytest
from fastapi import APIRouter
from fastapi.testclient import TestClient
from pydantic import BaseModel
from app.main import app

mock_router = APIRouter()


class SampleModel(BaseModel):
    name: str
    score: int


@mock_router.post("/test-validation")
def sample_validation_route(payload: SampleModel):
    return payload


@mock_router.get("/test-internal-error")
def sample_internal_error_route():
    # Intentionally trigger an unhandled error with sensitive stack trace
    raise RuntimeError("Sensitive database secret in error message: password=supersecret")


app.include_router(mock_router, prefix="/api/v1/test-harness")

client = TestClient(app, base_url="http://127.0.0.1")


def test_404_resource_not_found():
    """Verify that a nonexistent route returns structured 404 error envelope."""
    response = client.get("/api/v1/nonexistent-route-endpoint")
    assert response.status_code == 404
    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == "RESOURCE_NOT_FOUND"
    assert "Not Found" in data["error"]["message"]


def test_422_validation_error():
    """Verify that invalid request bodies return structured 422 error envelope."""
    response = client.post("/api/v1/test-harness/test-validation", json={"name": "test", "score": "not-an-int"})
    assert response.status_code == 422
    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == "VALIDATION_ERROR"
    assert "details" in data["error"]
    assert len(data["error"]["details"]) > 0


def test_500_internal_error_masks_details():
    """Verify unhandled exceptions do NOT leak internal stack traces or error strings."""
    safe_client = TestClient(app, base_url="http://127.0.0.1", raise_server_exceptions=False)
    response = safe_client.get("/api/v1/test-harness/test-internal-error")
    assert response.status_code == 500
    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == "INTERNAL_SERVER_ERROR"
    # Ensure sensitive string from the exception is NEVER leaked in the response
    assert "supersecret" not in response.text
    assert "RuntimeError" not in response.text
