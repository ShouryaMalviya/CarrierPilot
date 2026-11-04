"""Tests for practice attempt recording, deterministic grading, and attempt statistics."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.deps import get_db
from app.db.base import Base
from app.main import app
from app.models import Question
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
# Practice Attempt Tests
# ==============================================================================

class TestPracticeAttemptGrading:
    """Validate objective grading logic, feedback disclosure, and attempt tracking."""

    def test_submit_correct_attempt(self, client: TestClient, test_db: Session):
        """Submitting a correct answer awards 1.0 score and reveals educational explanation."""
        token = _get_auth_token(client, "student_attempt_1@example.com")
        headers = {"Authorization": f"Bearer {token}"}

        # Fetch first question from DB to know its true answer key
        q = test_db.query(Question).filter(Question.topic == "Python").first()
        assert q is not None

        # Submit the exact correct answer key (in lowercase to verify case-insensitivity)
        payload = {
            "question_id": q.id,
            "user_answer": q.answer_key.lower(),
            "duration_seconds": 18,
        }
        resp = client.post("/api/v1/practice/attempts", json=payload, headers=headers)
        assert resp.status_code == 201
        data = resp.json()

        assert data["question_id"] == q.id
        assert data["user_answer"] == q.answer_key.upper()
        assert data["is_correct"] is True
        assert data["score"] == 1.0
        assert data["correct_answer_key"] == q.answer_key.upper()
        assert len(data["explanation"]) > 10
        assert data["duration_seconds"] == 18

    def test_submit_incorrect_attempt(self, client: TestClient, test_db: Session):
        """Submitting an incorrect answer awards 0.0 score but reveals correct key and explanation."""
        token = _get_auth_token(client, "student_attempt_2@example.com")
        headers = {"Authorization": f"Bearer {token}"}

        q = test_db.query(Question).filter(Question.topic == "Python").first()
        assert q is not None

        # Pick an answer that is definitely wrong
        wrong_choice = "Z" if q.answer_key != "Z" else "Y"
        payload = {
            "question_id": q.id,
            "user_answer": wrong_choice,
            "duration_seconds": 30,
        }
        resp = client.post("/api/v1/practice/attempts", json=payload, headers=headers)
        assert resp.status_code == 201
        data = resp.json()

        assert data["is_correct"] is False
        assert data["score"] == 0.0
        assert data["correct_answer_key"] == q.answer_key.upper()
        assert data["explanation"] == q.explanation

    def test_submit_attempt_linked_to_session(self, client: TestClient, test_db: Session):
        """Attempts submitted with session_id link correctly and update session score."""
        token = _get_auth_token(client, "student_session_att@example.com")
        headers = {"Authorization": f"Bearer {token}"}

        # Create a practice session with 2 questions
        session_resp = client.post(
            "/api/v1/practice/sessions",
            json={"topic": "SQL", "question_count": 2},
            headers=headers,
        )
        session_id = session_resp.json()["session_id"]
        q1_id = session_resp.json()["questions"][0]["id"]

        q1 = test_db.get(Question, q1_id)
        assert q1 is not None

        # Submit correct attempt for question 1
        att_resp = client.post(
            "/api/v1/practice/attempts",
            json={
                "question_id": q1_id,
                "user_answer": q1.answer_key,
                "session_id": session_id,
                "duration_seconds": 15,
            },
            headers=headers,
        )
        assert att_resp.status_code == 201
        assert att_resp.json()["session_id"] == session_id

        # Verify session score updated (1 correct out of 2 = 50.0%)
        sess_check = client.get(f"/api/v1/practice/sessions/{session_id}", headers=headers)
        assert sess_check.status_code == 200
        assert sess_check.json()["score"] == 50.0

    def test_submit_attempt_with_invalid_session_rejected(self, client: TestClient, test_db: Session):
        """Attempt submission with invalid session_id returns 400 Bad Request."""
        token = _get_auth_token(client, "student_bad_sess@example.com")
        headers = {"Authorization": f"Bearer {token}"}

        q = test_db.query(Question).first()
        payload = {
            "question_id": q.id,
            "user_answer": "A",
            "session_id": "ps_nonexistent_12345",
        }
        resp = client.post("/api/v1/practice/attempts", json=payload, headers=headers)
        assert resp.status_code == 400

    def test_submit_attempt_nonexistent_question_rejected(self, client: TestClient):
        """Attempt submission for non-existent question_id returns 400."""
        token = _get_auth_token(client, "student_bad_q@example.com")
        headers = {"Authorization": f"Bearer {token}"}

        payload = {
            "question_id": 999999,
            "user_answer": "A",
        }
        resp = client.post("/api/v1/practice/attempts", json=payload, headers=headers)
        assert resp.status_code == 400

    def test_attempt_history_filtering_and_pagination(self, client: TestClient, test_db: Session):
        """Verify listing user attempts with topic and correctness filters."""
        token = _get_auth_token(client, "history_student@example.com")
        headers = {"Authorization": f"Bearer {token}"}

        py_q = test_db.query(Question).filter(Question.topic == "Python").first()
        sql_q = test_db.query(Question).filter(Question.topic == "SQL").first()

        # Submit 1 correct Python attempt
        client.post(
            "/api/v1/practice/attempts",
            json={"question_id": py_q.id, "user_answer": py_q.answer_key},
            headers=headers,
        )

        # Submit 1 incorrect SQL attempt
        client.post(
            "/api/v1/practice/attempts",
            json={"question_id": sql_q.id, "user_answer": "WRONG"},
            headers=headers,
        )

        # List all attempts (should be 2)
        all_att = client.get("/api/v1/practice/attempts", headers=headers)
        assert all_att.status_code == 200
        assert all_att.json()["total"] == 2

        # Filter by topic: Python
        py_att = client.get("/api/v1/practice/attempts?topic=Python", headers=headers)
        assert py_att.json()["total"] == 1
        assert py_att.json()["items"][0]["topic"] == "Python"
        assert py_att.json()["items"][0]["is_correct"] is True

        # Filter by is_correct: false
        wrong_att = client.get("/api/v1/practice/attempts?is_correct=false", headers=headers)
        assert wrong_att.json()["total"] == 1
        assert wrong_att.json()["items"][0]["topic"] == "SQL"
        assert wrong_att.json()["items"][0]["is_correct"] is False

    def test_attempt_ownership_isolation(self, client: TestClient, test_db: Session):
        """Users can only view their own practice attempts."""
        token_a = _get_auth_token(client, "student_a_isolation@example.com")
        token_b = _get_auth_token(client, "student_b_isolation@example.com")

        q = test_db.query(Question).first()

        # User A submits attempt
        client.post(
            "/api/v1/practice/attempts",
            json={"question_id": q.id, "user_answer": q.answer_key},
            headers={"Authorization": f"Bearer {token_a}"},
        )

        # User B queries attempts -> should see 0
        resp_b = client.get("/api/v1/practice/attempts", headers={"Authorization": f"Bearer {token_b}"})
        assert resp_b.status_code == 200
        assert resp_b.json()["total"] == 0

    def test_attempt_stats_summary(self, client: TestClient, test_db: Session):
        """Aggregate stats calculation across multiple attempts."""
        token = _get_auth_token(client, "student_stats@example.com")
        headers = {"Authorization": f"Bearer {token}"}

        py_q1 = test_db.query(Question).filter(Question.topic == "Python").first()
        py_q2 = test_db.query(Question).filter(Question.topic == "Python", Question.id != py_q1.id).first()
        devops_q = test_db.query(Question).filter(Question.topic == "DevOps").first()

        # 1 correct Python attempt (20s)
        client.post(
            "/api/v1/practice/attempts",
            json={"question_id": py_q1.id, "user_answer": py_q1.answer_key, "duration_seconds": 20},
            headers=headers,
        )

        # 1 incorrect Python attempt (10s)
        client.post(
            "/api/v1/practice/attempts",
            json={"question_id": py_q2.id, "user_answer": "WRONG", "duration_seconds": 10},
            headers=headers,
        )

        # 1 correct DevOps attempt (30s)
        client.post(
            "/api/v1/practice/attempts",
            json={"question_id": devops_q.id, "user_answer": devops_q.answer_key, "duration_seconds": 30},
            headers=headers,
        )

        # Fetch stats
        stats_resp = client.get("/api/v1/practice/attempts/stats", headers=headers)
        assert stats_resp.status_code == 200
        stats = stats_resp.json()

        assert stats["total_attempts"] == 3
        assert stats["correct_attempts"] == 2
        assert stats["accuracy_percentage"] == pytest.approx(66.7, 0.1)
        assert stats["total_time_seconds"] == 60
        assert "Python" in stats["by_topic"]
        assert stats["by_topic"]["Python"]["total_attempts"] == 2
        assert stats["by_topic"]["Python"]["correct_attempts"] == 1
        assert stats["by_topic"]["Python"]["accuracy_percentage"] == 50.0

    def test_unauthenticated_attempt_requests_rejected(self, client: TestClient):
        """Unauthenticated requests to attempt endpoints return 401."""
        assert client.post("/api/v1/practice/attempts", json={"question_id": 1, "user_answer": "A"}).status_code == 401
        assert client.get("/api/v1/practice/attempts").status_code == 401
        assert client.get("/api/v1/practice/attempts/stats").status_code == 401

