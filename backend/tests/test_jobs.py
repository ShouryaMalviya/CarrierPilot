"""Tests for job intake, skill requirement extraction, management, and synthetic fixtures."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.deps import get_db
from app.db.base import Base
from app.main import app
from app.models import Job, JobSkill, Skill
from app.services.job_parser import parse_job_skills, seed_synthetic_jobs


@event.listens_for(Engine, "connect")
def _set_sqlite_pragma(dbapi_connection, connection_record):
    """Enforce foreign key constraints in SQLite test engine."""
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


@pytest.fixture
def test_db():
    """Create an isolated in-memory test database and override get_db."""
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


def _get_auth_token(client: TestClient, email: str) -> str:
    """Helper to register and login a test user, returning their access token."""
    client.post("/api/v1/auth/register", json={"email": email, "password": "SecurePassword123!"})
    res = client.post("/api/v1/auth/login", json={"email": email, "password": "SecurePassword123!"})
    return res.json()["access_token"]


def test_parse_job_skills_unit():
    """Test deterministic extraction of required vs preferred skills from text."""
    text = (
        "Job Title: Backend Engineer\n\n"
        "Requirements:\n"
        "- Strong proficiency in Python and FastAPI\n"
        "- Experience with PostgreSQL database and Git\n\n"
        "Preferred Qualifications:\n"
        "- Hands-on experience with Docker or Kubernetes is a plus\n"
        "- Familiarity with AWS cloud services"
    )
    req, pref = parse_job_skills(text)

    assert "Python" in req
    assert "FastAPI" in req
    assert "PostgreSQL" in req
    assert "Git" in req

    assert "Docker" in pref
    assert "Kubernetes" in pref
    assert "AWS" in pref


def test_parse_job_skills_upgrade_to_required():
    """If a skill appears in preferred but is later specified as required, it is upgraded."""
    text = (
        "Preferred Qualifications:\n"
        "- Experience with Docker is nice to have\n\n"
        "Core Requirements:\n"
        "- Must have Docker production knowledge"
    )
    req, pref = parse_job_skills(text)
    assert "Docker" in req
    assert "Docker" not in pref


def test_job_create_auto_extraction(client: TestClient):
    """Creating a job parses required and preferred skills automatically."""
    token = _get_auth_token(client, "candidate1@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    payload = {
        "title": "Software Engineer, Full Stack",
        "company": "Tech Corp",
        "description": (
            "We are seeking a talented full-stack engineer.\n\n"
            "Requirements:\n"
            "Must be proficient in Python, React, and SQL.\n\n"
            "Preferred:\n"
            "Exposure to Docker is a bonus."
        ),
        "source_url": "https://example.com/jobs/123",
    }

    res = client.post("/api/v1/jobs", json=payload, headers=headers)
    assert res.status_code == 201
    data = res.json()

    assert data["title"] == payload["title"]
    assert data["company"] == payload["company"]
    assert data["is_synthetic"] is False
    assert data["is_active"] is True
    assert "Python" in data["required_skills"]
    assert "React" in data["required_skills"]
    assert "SQL" in data["required_skills"]
    assert "Docker" in data["preferred_skills"]
    assert len(data["skills"]) >= 4


def test_job_create_with_explicit_overrides(client: TestClient):
    """Creating a job with explicit required/preferred skills bypasses auto-extraction."""
    token = _get_auth_token(client, "candidate2@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    payload = {
        "title": "Custom Data Scientist",
        "company": "Data Insights LLC",
        "description": "General description text for a data scientist position...",
        "required_skills": ["Python", "Pandas", "Scikit-Learn"],
        "preferred_skills": ["PyTorch"],
    }

    res = client.post("/api/v1/jobs", json=payload, headers=headers)
    assert res.status_code == 201
    data = res.json()

    assert set(data["required_skills"]) == {"Python", "Pandas", "Scikit-Learn"}
    assert set(data["preferred_skills"]) == {"PyTorch"}


def test_seed_demo_jobs_and_list(client: TestClient):
    """Seeding benchmark jobs creates idempotent fixtures visible in job listings."""
    token = _get_auth_token(client, "user_demo@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    # Seed demo jobs
    seed_res = client.post("/api/v1/jobs/seed-demo", headers=headers)
    assert seed_res.status_code == 200
    seeded = seed_res.json()
    assert len(seeded) == 2
    assert all(j["is_synthetic"] is True for j in seeded)

    # Calling again is idempotent
    seed_res2 = client.post("/api/v1/jobs/seed-demo", headers=headers)
    assert seed_res2.status_code == 200

    # User creates a personal job
    client.post(
        "/api/v1/jobs",
        json={
            "title": "My Private Job",
            "description": "Requirements: Must know Python and Git.",
        },
        headers=headers,
    )

    # Listing returns both private and synthetic
    list_res = client.get("/api/v1/jobs", headers=headers)
    assert list_res.status_code == 200
    items = list_res.json()["jobs"]
    assert len(items) == 3

    # Filter synthetic only
    synth_res = client.get("/api/v1/jobs?is_synthetic=true", headers=headers)
    assert synth_res.status_code == 200
    assert len(synth_res.json()["jobs"]) == 2

    # Filter non-synthetic only
    user_res = client.get("/api/v1/jobs?is_synthetic=false", headers=headers)
    assert user_res.status_code == 200
    assert len(user_res.json()["jobs"]) == 1
    assert user_res.json()["jobs"][0]["title"] == "My Private Job"


def test_job_search_filter(client: TestClient):
    """Search query filters jobs by title, company, or description."""
    token = _get_auth_token(client, "searcher@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    client.post(
        "/api/v1/jobs",
        json={
            "title": "Golang Backend Developer",
            "company": "GoWorks Inc",
            "description": "Requirements: Must know Go and Docker.",
        },
        headers=headers,
    )
    client.post(
        "/api/v1/jobs",
        json={
            "title": "Rust Systems Engineer",
            "company": "Oxide Systems",
            "description": "Requirements: Must know Rust and C++.",
        },
        headers=headers,
    )

    # Search for "Golang"
    res = client.get("/api/v1/jobs?search=Golang", headers=headers)
    assert res.status_code == 200
    assert res.json()["total"] == 1
    assert res.json()["jobs"][0]["company"] == "GoWorks Inc"


def test_job_ownership_isolation(client: TestClient):
    """User B cannot view, edit, or delete User A's private job."""
    token_a = _get_auth_token(client, "alice@example.com")
    token_b = _get_auth_token(client, "bob@example.com")

    # Alice creates a private job
    res_a = client.post(
        "/api/v1/jobs",
        json={
            "title": "Alice's Target Job",
            "description": "Requirements: Must know Python and FastAPI.",
        },
        headers={"Authorization": f"Bearer {token_a}"},
    )
    job_id = res_a.json()["id"]

    # Bob attempts GET -> 404
    get_b = client.get(f"/api/v1/jobs/{job_id}", headers={"Authorization": f"Bearer {token_b}"})
    assert get_b.status_code == 404
    assert get_b.json()["error"]["code"] == "JOB_NOT_FOUND"

    # Bob attempts PUT -> 404
    put_b = client.put(
        f"/api/v1/jobs/{job_id}",
        json={"title": "Hacked Title"},
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert put_b.status_code == 404

    # Bob attempts DELETE -> 404
    del_b = client.delete(f"/api/v1/jobs/{job_id}", headers={"Authorization": f"Bearer {token_b}"})
    assert del_b.status_code == 404

    # Alice can still access her job
    get_a = client.get(f"/api/v1/jobs/{job_id}", headers={"Authorization": f"Bearer {token_a}"})
    assert get_a.status_code == 200
    assert get_a.json()["title"] == "Alice's Target Job"


def test_synthetic_job_immutability(client: TestClient):
    """Users cannot update or delete public synthetic demo benchmark jobs."""
    token = _get_auth_token(client, "user_synth@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    seed_res = client.post("/api/v1/jobs/seed-demo", headers=headers)
    synth_id = seed_res.json()[0]["id"]

    # Anyone can view the synthetic job
    get_res = client.get(f"/api/v1/jobs/{synth_id}", headers=headers)
    assert get_res.status_code == 200
    assert get_res.json()["is_synthetic"] is True

    # User cannot update synthetic job
    put_res = client.put(
        f"/api/v1/jobs/{synth_id}",
        json={"title": "Tampered Synthetic Job"},
        headers=headers,
    )
    assert put_res.status_code == 404

    # User cannot delete synthetic job
    del_res = client.delete(f"/api/v1/jobs/{synth_id}", headers=headers)
    assert del_res.status_code == 404


def test_job_update_reparses_skills(client: TestClient):
    """Updating a job's description automatically re-parses required skills."""
    token = _get_auth_token(client, "updater@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    create_res = client.post(
        "/api/v1/jobs",
        json={
            "title": "Backend Dev",
            "description": "Requirements: Must know Python and Git.",
        },
        headers=headers,
    )
    job_id = create_res.json()["id"]
    assert "Python" in create_res.json()["required_skills"]
    assert "Docker" not in create_res.json()["required_skills"]

    # Update description to add Docker and remove Python
    update_res = client.put(
        f"/api/v1/jobs/{job_id}",
        json={
            "description": "Requirements: Must know Docker and Kubernetes.",
        },
        headers=headers,
    )
    assert update_res.status_code == 200
    updated_skills = update_res.json()["required_skills"]
    assert "Docker" in updated_skills
    assert "Kubernetes" in updated_skills
    assert "Python" not in updated_skills


def test_job_delete(client: TestClient):
    """Owner can delete their job posting."""
    token = _get_auth_token(client, "deleter@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    create_res = client.post(
        "/api/v1/jobs",
        json={
            "title": "Temporary Job Posting",
            "description": "Requirements: Must have Python experience.",
        },
        headers=headers,
    )
    job_id = create_res.json()["id"]

    del_res = client.delete(f"/api/v1/jobs/{job_id}", headers=headers)
    assert del_res.status_code == 200

    get_res = client.get(f"/api/v1/jobs/{job_id}", headers=headers)
    assert get_res.status_code == 404


def test_job_validation_errors(client: TestClient):
    """Invalid payloads produce 422 unprocessable entity errors."""
    token = _get_auth_token(client, "validator@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    # Description too short
    res_short_desc = client.post(
        "/api/v1/jobs",
        json={"title": "Software Engineer", "description": "Too short"},
        headers=headers,
    )
    assert res_short_desc.status_code == 422

    # Title too short
    res_short_title = client.post(
        "/api/v1/jobs",
        json={"title": "X", "description": "Valid length description for software engineering role."},
        headers=headers,
    )
    assert res_short_title.status_code == 422


def test_job_unauthorized_access(client: TestClient):
    """Accessing jobs without a valid bearer token returns 401 Unauthorized."""
    res = client.get("/api/v1/jobs")
    assert res.status_code == 401

