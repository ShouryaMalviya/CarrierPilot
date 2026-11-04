"""Tests for Part 23 - Typed mock interview session workflow and question catalog."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.deps import get_db
from app.db.base import Base
from app.main import app
from app.models import InterviewSession, User
from app.schemas.interview import INTERVIEW_ETHICAL_DISCLAIMER


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


# ==============================================================================
# Question Catalog Tests
# ==============================================================================

class TestInterviewCatalog:
    """Validate mock interview curated question catalog and lookup endpoints."""

    def test_get_catalog_returns_all_curated_questions(self, client: TestClient):
        """Catalog endpoint returns curated technical prompts, roles, and competencies."""
        resp = client.get("/api/v1/interviews/catalog")
        assert resp.status_code == 200
        data = resp.json()

        assert data["total_questions"] >= 15
        assert len(data["questions"]) == data["total_questions"]
        assert "Full-Stack Engineer" in data["roles"]
        assert "Backend Engineer" in data["roles"]
        assert "System Design" in data["competencies"]
        assert "Coding & Algorithms" in data["competencies"]

    def test_get_catalog_filter_by_role_and_competency(self, client: TestClient):
        """Catalog filtering respects both role and competency query parameters."""
        resp = client.get("/api/v1/interviews/catalog?role=Backend%20Engineer&competency=System%20Design")
        assert resp.status_code == 200
        data = resp.json()

        assert data["total_questions"] >= 1
        for q in data["questions"]:
            assert q["role"] == "Backend Engineer"
            assert q["competency"] == "System Design"

    def test_get_curated_question_by_id(self, client: TestClient):
        """Lookup of a specific question by unique identifier returns details and key concepts."""
        resp = client.get("/api/v1/interviews/catalog/int-fs-sd-01")
        assert resp.status_code == 200
        data = resp.json()

        assert data["id"] == "int-fs-sd-01"
        assert "Collaborative Document Editor" in data["title"]
        assert "WebSockets" in data["key_concepts"]
        assert len(data["guidelines"]) > 0

    def test_get_nonexistent_curated_question_returns_404(self, client: TestClient):
        """Looking up an invalid question ID returns 404 Not Found."""
        resp = client.get("/api/v1/interviews/catalog/invalid-q-999")
        assert resp.status_code == 404


# ==============================================================================
# Mock Interview Session Lifecycle Tests
# ==============================================================================

class TestMockInterviewSessionWorkflow:
    """Validate typed interview session creation, submission, state changes, and isolation."""

    def test_create_session_with_default_profile_role(self, client: TestClient):
        """A user can initiate a mock interview session without specifying role/competency."""
        token = _get_auth_token(client, "candidate_default@example.com")
        headers = {"Authorization": f"Bearer {token}"}

        resp = client.post("/api/v1/interviews/sessions", json={}, headers=headers)
        assert resp.status_code == 201
        data = resp.json()

        assert data["id"] is not None
        assert data["status"] == "in_progress"
        assert len(data["question_text"]) > 10
        assert data["user_response"] is None
        assert data["rubric_version"] == "1.0.0"
        assert "disclaimer" in data
        assert "ethical" in data["disclaimer"].lower() or "predict" in data["disclaimer"].lower()

    def test_create_session_with_explicit_role_and_competency(self, client: TestClient):
        """A session can be initiated targeting a specific role and competency."""
        token = _get_auth_token(client, "candidate_be@example.com")
        headers = {"Authorization": f"Bearer {token}"}

        resp = client.post(
            "/api/v1/interviews/sessions",
            json={"role": "Backend Engineer", "competency": "DevOps & Cloud"},
            headers=headers,
        )
        assert resp.status_code == 201
        data = resp.json()

        assert data["role"] == "Backend Engineer"
        assert data["competency"] == "DevOps & Cloud"
        assert data["status"] == "in_progress"
        assert "Circuit Breaker" in data["question_text"] or len(data["question_text"]) > 20

    def test_create_session_with_specific_question_id(self, client: TestClient):
        """A session can be created directly referencing a curated question ID."""
        token = _get_auth_token(client, "candidate_specific_q@example.com")
        headers = {"Authorization": f"Bearer {token}"}

        resp = client.post(
            "/api/v1/interviews/sessions",
            json={"question_id": "int-be-ca-01"},
            headers=headers,
        )
        assert resp.status_code == 201
        data = resp.json()

        assert data["role"] == "Backend Engineer"
        assert data["competency"] == "Coding & Algorithms"
        assert "rate-limiting" in data["question_text"].lower() or "rate" in data["question_text"].lower()

    def test_create_session_with_custom_prompt(self, client: TestClient):
        """A candidate can provide their own custom interview prompt for practice."""
        token = _get_auth_token(client, "candidate_custom@example.com")
        headers = {"Authorization": f"Bearer {token}"}

        custom_prompt = "Explain how PostgreSQL MVCC handles write-write conflicts under Read Committed isolation."
        resp = client.post(
            "/api/v1/interviews/sessions",
            json={"custom_question_text": custom_prompt, "role": "Backend Engineer"},
            headers=headers,
        )
        assert resp.status_code == 201
        data = resp.json()

        assert data["question_text"] == custom_prompt
        assert data["role"] == "Backend Engineer"
        assert data["status"] == "in_progress"

    def test_create_session_invalid_question_id_returns_404(self, client: TestClient):
        """Attempting to initiate a session with an invalid question ID yields 404."""
        token = _get_auth_token(client, "candidate_invalid_q@example.com")
        headers = {"Authorization": f"Bearer {token}"}

        resp = client.post(
            "/api/v1/interviews/sessions",
            json={"question_id": "non-existent-question-abc"},
            headers=headers,
        )
        assert resp.status_code == 404

    def test_submit_valid_response(self, client: TestClient):
        """A candidate can submit a comprehensive typed response, transitioning status to 'submitted'."""
        token = _get_auth_token(client, "candidate_submit@example.com")
        headers = {"Authorization": f"Bearer {token}"}

        create_resp = client.post("/api/v1/interviews/sessions", json={}, headers=headers)
        session_id = create_resp.json()["id"]

        written_answer = (
            "To handle concurrent editing across multiple clients, I would use Conflict-Free Replicated "
            "Data Types (CRDTs) like Yjs or Automerge. The client maintains an in-memory document state "
            "and connects via WebSockets. Every local character insertion generates an idempotent operation "
            "with a lamport timestamp, which is broadcasted to the server and relayed to peer clients. "
            "For persistence, periodic snapshotting saves the document state to S3/Postgres every 30 seconds."
        )

        submit_resp = client.post(
            f"/api/v1/interviews/sessions/{session_id}/submit",
            json={"user_response": written_answer, "duration_seconds": 180},
            headers=headers,
        )
        assert submit_resp.status_code == 200
        data = submit_resp.json()

        assert data["id"] == session_id
        assert data["status"] == "submitted"
        assert data["user_response"] == written_answer

    def test_submit_response_too_short_rejected(self, client: TestClient):
        """Answers shorter than 20 non-whitespace characters are rejected with 400."""
        token = _get_auth_token(client, "candidate_short@example.com")
        headers = {"Authorization": f"Bearer {token}"}

        create_resp = client.post("/api/v1/interviews/sessions", json={}, headers=headers)
        session_id = create_resp.json()["id"]

        resp = client.post(
            f"/api/v1/interviews/sessions/{session_id}/submit",
            json={"user_response": "Too short"},
            headers=headers,
        )
        assert resp.status_code == 422 or resp.status_code == 400

    def test_cannot_resubmit_or_submit_to_non_in_progress_session(self, client: TestClient):
        """Submitting a response to an already submitted or abandoned session is rejected with 400."""
        token = _get_auth_token(client, "candidate_resubmit@example.com")
        headers = {"Authorization": f"Bearer {token}"}

        create_resp = client.post("/api/v1/interviews/sessions", json={}, headers=headers)
        session_id = create_resp.json()["id"]

        valid_answer = "This is a detailed and comprehensive technical response explaining the system design."
        sub_resp = client.post(
            f"/api/v1/interviews/sessions/{session_id}/submit",
            json={"user_response": valid_answer},
            headers=headers,
        )
        assert sub_resp.status_code == 200

        # Resubmit attempt
        second_resp = client.post(
            f"/api/v1/interviews/sessions/{session_id}/submit",
            json={"user_response": "Another attempt to overwrite the previously submitted answer."},
            headers=headers,
        )
        assert second_resp.status_code == 400

    def test_abandon_active_session(self, client: TestClient):
        """An active session can be explicitly abandoned by the candidate."""
        token = _get_auth_token(client, "candidate_abandon@example.com")
        headers = {"Authorization": f"Bearer {token}"}

        create_resp = client.post("/api/v1/interviews/sessions", json={}, headers=headers)
        session_id = create_resp.json()["id"]

        abandon_resp = client.post(f"/api/v1/interviews/sessions/{session_id}/abandon", headers=headers)
        assert abandon_resp.status_code == 200
        assert abandon_resp.json()["status"] == "abandoned"

        # Cannot submit to abandoned session
        sub_resp = client.post(
            f"/api/v1/interviews/sessions/{session_id}/submit",
            json={"user_response": "A detailed technical response after abandoning session."},
            headers=headers,
        )
        assert sub_resp.status_code == 400

    def test_cannot_abandon_already_abandoned_session(self, client: TestClient):
        """Attempting to abandon an already abandoned session returns 400."""
        token = _get_auth_token(client, "candidate_double_abandon@example.com")
        headers = {"Authorization": f"Bearer {token}"}

        create_resp = client.post("/api/v1/interviews/sessions", json={}, headers=headers)
        session_id = create_resp.json()["id"]

        client.post(f"/api/v1/interviews/sessions/{session_id}/abandon", headers=headers)
        second_abandon = client.post(f"/api/v1/interviews/sessions/{session_id}/abandon", headers=headers)
        assert second_abandon.status_code == 400

    def test_list_user_sessions_with_filters_and_pagination(self, client: TestClient):
        """Session listing correctly filters by role, status, and supports pagination."""
        token = _get_auth_token(client, "candidate_listing@example.com")
        headers = {"Authorization": f"Bearer {token}"}

        # Create 3 sessions
        s1 = client.post(
            "/api/v1/interviews/sessions",
            json={"role": "Backend Engineer", "competency": "System Design"},
            headers=headers,
        ).json()["id"]

        s2 = client.post(
            "/api/v1/interviews/sessions",
            json={"role": "Frontend Engineer", "competency": "System Design"},
            headers=headers,
        ).json()["id"]

        s3 = client.post(
            "/api/v1/interviews/sessions",
            json={"role": "Backend Engineer", "competency": "Database & SQL"},
            headers=headers,
        ).json()["id"]

        # Abandon s3
        client.post(f"/api/v1/interviews/sessions/{s3}/abandon", headers=headers)

        # List all
        resp = client.get("/api/v1/interviews/sessions", headers=headers)
        assert resp.status_code == 200
        assert resp.json()["total"] == 3

        # Filter by role
        resp_be = client.get("/api/v1/interviews/sessions?role=Backend%20Engineer", headers=headers)
        assert resp_be.status_code == 200
        assert resp_be.json()["total"] == 2

        # Filter by status
        resp_ab = client.get("/api/v1/interviews/sessions?status=abandoned", headers=headers)
        assert resp_ab.status_code == 200
        assert resp_ab.json()["total"] == 1
        assert resp_ab.json()["sessions"][0]["id"] == s3

    def test_interview_session_ownership_isolation(self, client: TestClient):
        """User A's sessions are completely inaccessible to User B (404 isolation)."""
        token_a = _get_auth_token(client, "user_a_interview@example.com")
        token_b = _get_auth_token(client, "user_b_interview@example.com")

        headers_a = {"Authorization": f"Bearer {token_a}"}
        headers_b = {"Authorization": f"Bearer {token_b}"}

        create_resp = client.post("/api/v1/interviews/sessions", json={}, headers=headers_a)
        session_id = create_resp.json()["id"]

        # User B attempts to view User A's session
        get_b = client.get(f"/api/v1/interviews/sessions/{session_id}", headers=headers_b)
        assert get_b.status_code == 404

        # User B attempts to submit response to User A's session
        sub_b = client.post(
            f"/api/v1/interviews/sessions/{session_id}/submit",
            json={"user_response": "Malicious attempt to answer another user's session."},
            headers=headers_b,
        )
        assert sub_b.status_code == 404

        # User B attempts to abandon User A's session
        ab_b = client.post(f"/api/v1/interviews/sessions/{session_id}/abandon", headers=headers_b)
        assert ab_b.status_code == 404

        # User B's session list does not contain User A's session
        list_b = client.get("/api/v1/interviews/sessions", headers=headers_b)
        assert list_b.status_code == 200
        assert list_b.json()["total"] == 0

    def test_unauthenticated_requests_rejected(self, client: TestClient):
        """All private session endpoints reject unauthenticated requests with 401."""
        assert client.post("/api/v1/interviews/sessions", json={}).status_code == 401
        assert client.get("/api/v1/interviews/sessions").status_code == 401
        assert client.get("/api/v1/interviews/sessions/1").status_code == 401
        assert client.post("/api/v1/interviews/sessions/1/submit", json={"user_response": "foo"}).status_code == 401
        assert client.post("/api/v1/interviews/sessions/1/abandon").status_code == 401

