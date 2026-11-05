"""Contract test verifying the exact API payloads and flows used by the frontend Auth & Onboarding screens."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.deps import get_db
from app.db.base import Base
from app.main import app


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


class TestAuthOnboardingFrontendContract:
    """Verifies that the backend API matches the frontend AuthContext and OnboardingPage contracts."""

    def test_complete_registration_login_and_onboarding_flow(self, client):
        candidate_email = "new_candidate_onboarding@example.com"
        candidate_password = "SecurePassword123!"

        # 1. Candidate Registration (RegisterPage)
        reg_response = client.post(
            "/api/v1/auth/register",
            json={"email": candidate_email, "password": candidate_password},
        )
        assert reg_response.status_code == 201
        reg_data = reg_response.json()
        assert reg_data["email"] == candidate_email
        assert "id" in reg_data
        assert reg_data["is_active"] is True

        # 2. Candidate Login (LoginPage)
        login_response = client.post(
            "/api/v1/auth/login",
            json={"email": candidate_email, "password": candidate_password},
        )
        assert login_response.status_code == 200
        token_data = login_response.json()
        assert "access_token" in token_data
        assert token_data["token_type"] == "bearer"
        assert token_data["expires_in"] > 0
        token = token_data["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # 3. Fetch User Profile (AuthContext me & profile)
        me_response = client.get("/api/v1/auth/me", headers=headers)
        assert me_response.status_code == 200
        me_data = me_response.json()
        assert me_data["email"] == candidate_email

        # 4. Fetch Onboarding Disclosures (OnboardingPage Step 3)
        disclosure_res = client.get("/api/v1/profile/onboarding-info")
        assert disclosure_res.status_code == 200
        disclosure = disclosure_res.json()
        assert "purpose" in disclosure
        assert "disclaimers" in disclosure
        assert len(disclosure["disclaimers"]) >= 3
        # Check mandatory non-hiring and educational terms
        disclaimers_str = " ".join(disclosure["disclaimers"]).lower()
        assert "educational" in disclaimers_str
        assert "predict" in disclaimers_str or "guarantee" in disclaimers_str
        assert disclosure["camera_or_mic_required"] is False

        # 5. Fetch Target Role Presets (OnboardingPage Step 1)
        roles_res = client.get("/api/v1/profile/roles")
        assert roles_res.status_code == 200
        roles = roles_res.json()
        assert isinstance(roles, list)
        assert len(roles) >= 3
        assert "Junior Python Developer" in roles

        # 6. Initial Profile State Check
        initial_profile_res = client.get("/api/v1/profile", headers=headers)
        assert initial_profile_res.status_code == 200
        initial_profile = initial_profile_res.json()
        assert initial_profile["target_role"] == "Junior Python Developer"

        # 7. Submit Onboarding Preferences (OnboardingPage Submit)
        update_res = client.put(
            "/api/v1/profile",
            headers=headers,
            json={
                "target_role": "Full-Stack Web Engineer",
                "preferred_language": "English",
                "consent_analytics": True,
            },
        )
        assert update_res.status_code == 200
        updated_profile = update_res.json()
        assert updated_profile["target_role"] == "Full-Stack Web Engineer"
        assert updated_profile["preferred_language"] == "English"
        assert updated_profile["consent_analytics"] is True

        # 8. Re-fetch Profile to confirm persistence
        refetched_profile_res = client.get("/api/v1/profile", headers=headers)
        assert refetched_profile_res.status_code == 200
        assert refetched_profile_res.json()["target_role"] == "Full-Stack Web Engineer"

    def test_duplicate_registration_rejected(self, client):
        email = "duplicate_test@example.com"
        password = "Password123!"

        res1 = client.post("/api/v1/auth/register", json={"email": email, "password": password})
        assert res1.status_code == 201

        res2 = client.post("/api/v1/auth/register", json={"email": email, "password": password})
        assert res2.status_code == 400
        error_json = res2.json()
        error_code = error_json.get("error", {}).get("code") or error_json.get("detail", {}).get("code")
        assert error_code == "EMAIL_ALREADY_REGISTERED"

    def test_invalid_login_rejected(self, client):
        res = client.post(
            "/api/v1/auth/login",
            json={"email": "nonexistent@example.com", "password": "WrongPassword!"},
        )
        assert res.status_code == 401
        error_json = res.json()
        error_code = error_json.get("error", {}).get("code") or error_json.get("detail", {}).get("code")
        assert error_code == "INVALID_CREDENTIALS"

    def test_unauthenticated_profile_update_rejected(self, client):
        res = client.put(
            "/api/v1/profile",
            json={"target_role": "Hacker Role"},
        )
        assert res.status_code == 401
