"""Tests for diagnostic practice sessions: lifecycle, progressive delivery, and ownership isolation."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.deps import get_db
from app.db.base import Base
from app.main import app
from app.services.question_service import seed_questions


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
    seed_questions(session)  # Seed benchmark questions into the test DB
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
# Practice Session Tests
# ==============================================================================

class TestPracticeSessionLifecycle:
    """Validate diagnostic practice session creation, prompt delivery, and progression."""

    def test_create_session_success(self, client: TestClient):
        """Create a diagnostic practice session and verify public question delivery."""
        token = _get_auth_token(client, "student1@example.com")
        headers = {"Authorization": f"Bearer {token}"}

        payload = {
            "topic": "Python",
            "difficulty": "easy",
            "question_count": 2,
            "time_limit_seconds": 600,
        }
        resp = client.post("/api/v1/practice/sessions", json=payload, headers=headers)
        assert resp.status_code == 201
        data = resp.json()

        assert data["session_id"].startswith("ps_")
        assert data["topic"] == "Python"
        assert data["total_questions"] == 2
        assert data["current_index"] == 0
        assert data["status"] == "in_progress"
        assert data["time_limit_seconds"] == 600
        assert data["has_next"] is True
        assert len(data["questions"]) == 2

        # Critical security & integrity check: answer_key & explanation MUST NOT be present
        for q in data["questions"]:
            assert "answer_key" not in q, "SECURITY LEAK: answer_key found in session question payload!"
            assert "explanation" not in q, "LEAK: explanation found in session question payload!"
            assert "prompt" in q
            assert len(q["options"]) >= 2

        # Current question should match the first item
        current_q = data["current_question"]
        assert current_q is not None
        assert current_q["id"] == data["questions"][0]["id"]
        assert "answer_key" not in current_q

    def test_progressive_question_delivery(self, client: TestClient):
        """Step through a multi-question session and verify index increment and completion."""
        token = _get_auth_token(client, "student2@example.com")
        headers = {"Authorization": f"Bearer {token}"}

        # Create a session with 3 questions
        create_resp = client.post(
            "/api/v1/practice/sessions",
            json={"topic": "Data Structures", "question_count": 3},
            headers=headers,
        )
        assert create_resp.status_code == 201
        session_id = create_resp.json()["session_id"]
        questions = create_resp.json()["questions"]
        assert len(questions) == 3

        # Initial state: Index 0
        get_resp = client.get(f"/api/v1/practice/sessions/{session_id}", headers=headers)
        assert get_resp.status_code == 200
        state0 = get_resp.json()
        assert state0["current_index"] == 0
        assert state0["current_question"]["id"] == questions[0]["id"]
        assert state0["has_next"] is True
        assert state0["progress_percentage"] == 0.0

        # Advance to question 2 (Index 1)
        next_resp1 = client.post(f"/api/v1/practice/sessions/{session_id}/next", headers=headers)
        assert next_resp1.status_code == 200
        state1 = next_resp1.json()
        assert state1["current_index"] == 1
        assert state1["current_question"]["id"] == questions[1]["id"]
        assert state1["has_next"] is True
        assert state1["progress_percentage"] == pytest.approx(33.3, 0.1)

        # Advance to question 3 (Index 2)
        next_resp2 = client.post(f"/api/v1/practice/sessions/{session_id}/next", headers=headers)
        assert next_resp2.status_code == 200
        state2 = next_resp2.json()
        assert state2["current_index"] == 2
        assert state2["current_question"]["id"] == questions[2]["id"]
        assert state2["has_next"] is False
        assert state2["progress_percentage"] == pytest.approx(66.7, 0.1)

        # Advance past last question -> Completes session
        next_resp3 = client.post(f"/api/v1/practice/sessions/{session_id}/next", headers=headers)
        assert next_resp3.status_code == 200
        state3 = next_resp3.json()
        assert state3["current_index"] == 3
        assert state3["status"] == "completed"
        assert state3["current_question"] is None
        assert state3["progress_percentage"] == 100.0
        assert state3["completed_at"] is not None

        # Advancing an already-completed session returns 400
        err_resp = client.post(f"/api/v1/practice/sessions/{session_id}/next", headers=headers)
        assert err_resp.status_code == 400
        err_data = err_resp.json()
        error_msg = err_data.get("error", {}).get("message") or err_data.get("detail", "")
        assert "Cannot advance session with status 'completed'" in error_msg

    def test_abandon_session(self, client: TestClient):
        """Abandoning an in-progress session terminates question progression."""
        token = _get_auth_token(client, "student3@example.com")
        headers = {"Authorization": f"Bearer {token}"}

        create_resp = client.post(
            "/api/v1/practice/sessions",
            json={"topic": "SQL", "question_count": 2},
            headers=headers,
        )
        session_id = create_resp.json()["session_id"]

        abandon_resp = client.post(f"/api/v1/practice/sessions/{session_id}/abandon", headers=headers)
        assert abandon_resp.status_code == 200
        abandon_data = abandon_resp.json()
        assert abandon_data["status"] == "abandoned"
        assert abandon_data["current_question"] is None
        assert abandon_data["completed_at"] is not None

    def test_session_ownership_isolation(self, client: TestClient):
        """Users can only access their own practice sessions."""
        token_a = _get_auth_token(client, "user_a@example.com")
        token_b = _get_auth_token(client, "user_b@example.com")

        # User A creates a session
        resp_a = client.post(
            "/api/v1/practice/sessions",
            json={"topic": "Python", "question_count": 2},
            headers={"Authorization": f"Bearer {token_a}"},
        )
        session_a_id = resp_a.json()["session_id"]

        # User B cannot access User A's session (returns 404)
        get_b = client.get(
            f"/api/v1/practice/sessions/{session_a_id}",
            headers={"Authorization": f"Bearer {token_b}"},
        )
        assert get_b.status_code == 404

        # User B cannot advance User A's session
        next_b = client.post(
            f"/api/v1/practice/sessions/{session_a_id}/next",
            headers={"Authorization": f"Bearer {token_b}"},
        )
        assert next_b.status_code == 404

        # User B listing sessions does not show User A's session
        list_b = client.get(
            "/api/v1/practice/sessions",
            headers={"Authorization": f"Bearer {token_b}"},
        )
        assert list_b.status_code == 200
        assert list_b.json()["total"] == 0

    def test_unauthenticated_session_endpoints_rejected(self, client: TestClient):
        """Unauthenticated requests to session endpoints are rejected with 401."""
        assert client.post("/api/v1/practice/sessions", json={"topic": "Python"}).status_code == 401
        assert client.get("/api/v1/practice/sessions").status_code == 401
        assert client.get("/api/v1/practice/sessions/ps_12345").status_code == 401
        assert client.post("/api/v1/practice/sessions/ps_12345/next").status_code == 401
        assert client.post("/api/v1/practice/sessions/ps_12345/abandon").status_code == 401

    def test_list_sessions_filter_by_status(self, client: TestClient):
        """Filter practice sessions list by status (in_progress vs abandoned)."""
        token = _get_auth_token(client, "student_multi@example.com")
        headers = {"Authorization": f"Bearer {token}"}

        # Create session 1 (leave in_progress)
        s1 = client.post(
            "/api/v1/practice/sessions", json={"topic": "Web Development"}, headers=headers
        ).json()

        # Create session 2 (abandon it)
        s2 = client.post(
            "/api/v1/practice/sessions", json={"topic": "DevOps"}, headers=headers
        ).json()
        client.post(f"/api/v1/practice/sessions/{s2['session_id']}/abandon", headers=headers)

        # List all
        all_resp = client.get("/api/v1/practice/sessions", headers=headers)
        assert all_resp.json()["total"] == 2

        # Filter in_progress
        prog_resp = client.get("/api/v1/practice/sessions?status=in_progress", headers=headers)
        assert prog_resp.json()["total"] == 1
        assert prog_resp.json()["items"][0]["session_id"] == s1["session_id"]

        # Filter abandoned
        aband_resp = client.get("/api/v1/practice/sessions?status=abandoned", headers=headers)
        assert aband_resp.json()["total"] == 1
        assert aband_resp.json()["items"][0]["session_id"] == s2["session_id"]
