"""Integration tests for application entry point and health check endpoints."""

import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app, base_url="http://127.0.0.1")


def test_root_endpoint():
    """Verify the root endpoint returns basic API metadata."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "online"
    assert data["name"] == "CareerPilot AI API"
    assert "version" in data


def test_root_health_endpoint():
    """Verify the top-level /health endpoint returns healthy status payload."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "environment" in data
    assert "version" in data
    assert "timestamp" in data
    assert "services" in data
    assert data["services"]["database"] == "configured"
    assert data["services"]["ai_provider"] == "local"
    assert data["services"]["semantic_embeddings"] is False


def test_api_v1_health_endpoint():
    """Verify /api/v1/health returns matching healthy status payload."""
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["environment"] == "development"


def test_cors_headers_allowed_origin():
    """Verify CORS headers are returned for configured frontend origins."""
    headers = {
        "Origin": "http://localhost:5173",
        "Access-Control-Request-Method": "GET",
    }
    response = client.options("/api/v1/health", headers=headers)
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "http://localhost:5173"
    assert response.headers.get("access-control-allow-credentials") == "true"


def test_cors_headers_disallowed_origin():
    """Verify CORS headers are NOT returned for unauthorized external origins."""
    headers = {
        "Origin": "http://unauthorized-evil-site.com",
        "Access-Control-Request-Method": "GET",
    }
    response = client.options("/api/v1/health", headers=headers)
    assert response.headers.get("access-control-allow-origin") is None
