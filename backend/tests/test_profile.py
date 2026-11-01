"""Integration tests for user profile CRUD and onboarding disclosure APIs."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.deps import get_db
from app.db.base import Base
from app.main import app
from app.models import Profile, User


@event.listens_for(Engine, "connect")
def _set_sqlite_pragma(dbapi_connection, connection_record):
    """Enforce foreign key constraints in SQLite test engine."""
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


@pytest.fixture
def test_db():
    """Create an isolated in-memory test database with StaticPool."""
    test_engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=False,
    )
    Base.metadata.create_all(bind=test_engine)
    test_sessionmaker = sessionmaker(bind=test_engine, expire_on_commit=False)

    def override_get_db():
        db = test_sessionmaker()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db

    session = test_sessionmaker()
    yield session

    session.close()
    Base.metadata.drop_all(bind=test_engine)
    app.dependency_overrides.pop(get_db, None)


@pytest.fixture
def client(test_db):
    """Provide a TestClient connected to the overridden test database."""
    return TestClient(app, base_url="http://127.0.0.1")


def _get_auth_token(client: TestClient, email: str, password: str = "SecurePass123!") -> str:
    """Helper to register and login a test user, returning their access token."""
    client.post("/api/v1/auth/register", json={"email": email, "password": password})
    res = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    return res.json()["access_token"]


def test_get_my_profile_authenticated(client):
    """Verify authenticated user can retrieve their auto-created profile."""
    token = _get_auth_token(client, "profile_user@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    response = client.get("/api/v1/profile", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["target_role"] == "Junior Python Developer"
    assert data["preferred_language"] == "English"
    assert data["consent_analytics"] is True
    assert "id" in data
    assert "user_id" in data


def test_update_my_profile_target_role(client, test_db):
    """Verify user can update their target role and preferences."""
    token = _get_auth_token(client, "updater@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    update_payload = {
        "target_role": "Entry-Level Data/ML Analyst",
        "preferred_language": "Hindi",
        "consent_analytics": False,
    }
    response = client.put("/api/v1/profile", json=update_payload, headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["target_role"] == "Entry-Level Data/ML Analyst"
    assert data["preferred_language"] == "Hindi"
    assert data["consent_analytics"] is False

    # Check persistence in database
    profile = test_db.query(Profile).filter_by(target_role="Entry-Level Data/ML Analyst").first()
    assert profile is not None
    assert profile.preferred_language == "Hindi"


def test_update_profile_partial_field(client):
    """Verify updating a single field leaves other preferences unchanged."""
    token = _get_auth_token(client, "partial_updater@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    # Update only preferred_language
    response = client.put("/api/v1/profile", json={"preferred_language": "French"}, headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["preferred_language"] == "French"
    assert data["target_role"] == "Junior Python Developer"  # Default preserved
    assert data["consent_analytics"] is True  # Default preserved


def test_profile_ownership_isolation(client):
    """Verify User A cannot see or modify User B's profile."""
    token_a = _get_auth_token(client, "user_a@example.com")
    token_b = _get_auth_token(client, "user_b@example.com")

    # User A customizes their profile
    client.put(
        "/api/v1/profile",
        json={"target_role": "Associate Frontend Developer"},
        headers={"Authorization": f"Bearer {token_a}"},
    )

    # User B checks their profile — it must remain their own default
    res_b = client.get("/api/v1/profile", headers={"Authorization": f"Bearer {token_b}"})
    assert res_b.status_code == 200
    assert res_b.json()["target_role"] == "Junior Python Developer"

    # User A checks their profile — it retains their updated role
    res_a = client.get("/api/v1/profile", headers={"Authorization": f"Bearer {token_a}"})
    assert res_a.status_code == 200
    assert res_a.json()["target_role"] == "Associate Frontend Developer"


def test_update_profile_validation_rejects_empty_string(client):
    """Verify that invalid/empty target_role string is rejected with 422."""
    token = _get_auth_token(client, "validator@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    response = client.put("/api/v1/profile", json={"target_role": "A"}, headers=headers)
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_list_supported_target_roles(client):
    """Verify endpoint returns default curated target roles."""
    response = client.get("/api/v1/profile/roles")
    assert response.status_code == 200
    roles = response.json()
    assert isinstance(roles, list)
    assert "Junior Python Developer" in roles
    assert "Entry-Level Data/ML Analyst" in roles


def test_onboarding_disclosure_metadata(client):
    """Verify onboarding disclosure emphasizes coaching and disclaims hiring predictions."""
    response = client.get("/api/v1/profile/onboarding-info")
    assert response.status_code == 200
    data = response.json()
    assert "purpose" in data
    assert "disclaimers" in data
    assert data["camera_or_mic_required"] is False
    disclaimer_text = " ".join(data["disclaimers"]).lower()
    assert "hiring" in disclaimer_text
    assert "guarantee" in disclaimer_text

