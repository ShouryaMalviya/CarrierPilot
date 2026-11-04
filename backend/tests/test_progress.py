"""Tests for learner progress telemetry, streaks, readiness index, and dashboard aggregates."""

from datetime import datetime, timedelta, timezone
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.deps import get_db
from app.db.base import Base
from app.main import app
from app.models import PracticeAttempt, Question, Resume, User
from app.services.progress_service import calculate_user_streak
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
# Progress & Dashboard Tests
# ==============================================================================

class TestLearnerProgressDashboard:
    """Validate dashboard telemetry aggregates, streaks, readiness scoring, and zero-states."""

    def test_zero_state_dashboard_new_user(self, client: TestClient):
        """A new user with zero activity receives complete, valid zero-state metrics without errors."""
        token = _get_auth_token(client, "zero_state_user@example.com")
        headers = {"Authorization": f"Bearer {token}"}

        resp = client.get("/api/v1/progress/dashboard", headers=headers)
        assert resp.status_code == 200
        data = resp.json()

        assert data["streak_days"] == 0
        assert data["longest_streak_days"] == 0
        assert data["total_attempts"] == 0
        assert data["correct_attempts"] == 0
        assert data["overall_accuracy_percentage"] == 0.0
        assert data["completed_sessions_count"] == 0
        assert data["active_sessions_count"] == 0

        # Readiness breakdown
        readiness = data["readiness"]
        assert readiness["overall_readiness_score"] == 0.0
        assert readiness["profile_resume_score"] == 0.0
        assert readiness["practice_mastery_score"] == 0.0
        assert readiness["readiness_level"] == "beginner"
        assert "predict" in readiness["disclaimer"].lower() or "guarantee" in readiness["disclaimer"].lower()

        # All topics should be marked unattempted
        assert len(data["topic_masteries"]) >= 5
        for m in data["topic_masteries"]:
            assert m["status_tier"] == "unattempted"
            assert m["mastery_score"] == 0.0
            assert m["recent_attempts_count"] == 0

        # Activity timeline has 14 entries with 0 attempts
        assert len(data["activity_timeline"]) == 14
        assert all(day["attempt_count"] == 0 for day in data["activity_timeline"])

        # Next action card prompts resume upload
        assert data["next_action"]["action_type"] == "upload_resume"

    def test_streak_calculation_unit(self, test_db: Session):
        """Validate consecutive calendar-day streak computation logic."""
        user = User(email="streak_tester@example.com", hashed_password="pw", is_active=True, is_verified=True)
        test_db.add(user)
        test_db.commit()
        test_db.refresh(user)

        q = test_db.query(Question).first()
        now = datetime.now(timezone.utc)

        # 0 attempts -> 0 streak
        curr, longest, last_date = calculate_user_streak(test_db, user.id)
        assert curr == 0
        assert longest == 0
        assert last_date is None

        # 1 attempt today -> 1 day streak
        att1 = PracticeAttempt(
            user_id=user.id,
            question_id=q.id,
            user_answer="A",
            is_correct=True,
            score=1.0,
            created_at=now,
        )
        test_db.add(att1)
        test_db.commit()

        curr, longest, last_date = calculate_user_streak(test_db, user.id)
        assert curr == 1
        assert longest == 1
        assert last_date == now.date().isoformat()

        # Add attempt yesterday -> 2 day streak
        att2 = PracticeAttempt(
            user_id=user.id,
            question_id=q.id,
            user_answer="A",
            is_correct=True,
            score=1.0,
            created_at=now - timedelta(days=1),
        )
        test_db.add(att2)
        test_db.commit()

        curr, longest, _ = calculate_user_streak(test_db, user.id)
        assert curr == 2
        assert longest == 2

    def test_active_user_dashboard_aggregates(self, client: TestClient, test_db: Session):
        """Active user activity is accurately summarized across mastery, readiness, and timeline."""
        token = _get_auth_token(client, "active_dashboard_student@example.com")
        headers = {"Authorization": f"Bearer {token}"}

        # 1. Simulate parsed resume
        user = test_db.query(User).filter(User.email == "active_dashboard_student@example.com").first()
        resume = Resume(
            user_id=user.id,
            original_filename="alex_resume.pdf",
            file_key="dummy_key",
            file_path="dummy_path",
            file_size_bytes=1024,
            mime_type="application/pdf",
            parser_version="1.0.0",
            parse_status="completed",
        )
        test_db.add(resume)
        test_db.commit()

        # 2. Submit practice attempts: 2 correct, 1 incorrect
        py_q1 = test_db.query(Question).filter(Question.topic == "Python").first()
        py_q2 = test_db.query(Question).filter(Question.topic == "Python", Question.id != py_q1.id).first()

        client.post(
            "/api/v1/practice/attempts",
            json={"question_id": py_q1.id, "user_answer": py_q1.answer_key, "duration_seconds": 25},
            headers=headers,
        )
        client.post(
            "/api/v1/practice/attempts",
            json={"question_id": py_q2.id, "user_answer": "WRONG", "duration_seconds": 15},
            headers=headers,
        )

        resp = client.get("/api/v1/progress/dashboard", headers=headers)
        assert resp.status_code == 200
        data = resp.json()

        assert data["total_attempts"] == 2
        assert data["correct_attempts"] == 1
        assert data["overall_accuracy_percentage"] == 50.0
        assert data["total_practice_time_seconds"] == 40
        assert data["streak_days"] == 1

        # Readiness has increased due to completed resume and practice
        readiness = data["readiness"]
        assert readiness["profile_resume_score"] == 100.0
        assert readiness["practice_mastery_score"] > 0.0
        assert readiness["overall_readiness_score"] > 0.0

        # Activity timeline shows 2 attempts today
        today_iso = datetime.now(timezone.utc).date().isoformat()
        today_activity = next(d for d in data["activity_timeline"] if d["date"] == today_iso)
        assert today_activity["attempt_count"] == 2
        assert today_activity["correct_count"] == 1

    def test_streak_endpoint(self, client: TestClient):
        """GET /api/v1/progress/streak returns current and longest streak values."""
        token = _get_auth_token(client, "streak_api_user@example.com")
        headers = {"Authorization": f"Bearer {token}"}

        resp = client.get("/api/v1/progress/streak", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "current_streak_days" in data
        assert "longest_streak_days" in data

    def test_readiness_endpoint(self, client: TestClient):
        """GET /api/v1/progress/readiness returns component factor breakdown."""
        token = _get_auth_token(client, "readiness_api_user@example.com")
        headers = {"Authorization": f"Bearer {token}"}

        resp = client.get("/api/v1/progress/readiness", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "overall_readiness_score" in data
        assert "profile_resume_score" in data
        assert "practice_mastery_score" in data
        assert "job_matching_score" in data
        assert "mock_interview_score" in data
        assert "readiness_level" in data

    def test_progress_ownership_isolation(self, client: TestClient, test_db: Session):
        """User A's practice activity does not contaminate User B's dashboard."""
        token_a = _get_auth_token(client, "user_a_prog@example.com")
        token_b = _get_auth_token(client, "user_b_prog@example.com")

        q = test_db.query(Question).first()

        # User A makes 3 attempts
        for _ in range(3):
            client.post(
                "/api/v1/practice/attempts",
                json={"question_id": q.id, "user_answer": q.answer_key, "duration_seconds": 20},
                headers={"Authorization": f"Bearer {token_a}"},
            )

        # Check User A's dashboard
        data_a = client.get("/api/v1/progress/dashboard", headers={"Authorization": f"Bearer {token_a}"}).json()
        assert data_a["total_attempts"] == 3

        # Check User B's dashboard -> must remain strictly 0
        data_b = client.get("/api/v1/progress/dashboard", headers={"Authorization": f"Bearer {token_b}"}).json()
        assert data_b["total_attempts"] == 0
        assert data_b["streak_days"] == 0

    def test_unauthenticated_progress_requests_rejected(self, client: TestClient):
        """Unauthenticated requests to progress endpoints return 401."""
        assert client.get("/api/v1/progress/dashboard").status_code == 401
        assert client.get("/api/v1/progress/streak").status_code == 401
        assert client.get("/api/v1/progress/readiness").status_code == 401
