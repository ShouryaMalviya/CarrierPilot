"""Tests for rule-based adaptive question recommendation and structured study plans."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.deps import get_db
from app.db.base import Base
from app.main import app
from app.models import Profile, Question
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
# Recommendation & Study Plan Tests
# ==============================================================================

class TestAdaptiveRecommendations:
    """Validate rule-based question selection, study plan generation, and audit logging."""

    def test_recommend_next_question_new_user_unpracticed(self, client: TestClient):
        """A new user receives an UNPRACTICED_CORE_DOMAIN recommendation without leaked answers."""
        token = _get_auth_token(client, "new_student_rec@example.com")
        headers = {"Authorization": f"Bearer {token}"}

        resp = client.get("/api/v1/practice/recommendations/next-question", headers=headers)
        assert resp.status_code == 200
        data = resp.json()

        assert data["reason_code"] == "UNPRACTICED_CORE_DOMAIN"
        assert data["priority_level"] == "high"
        assert "unpracticed" in data["rationale"].lower() or "not completed any practice" in data["rationale"].lower()
        assert data["topic_mastery_score"] == 0.0

        # Critical security check: answer_key & explanation must NOT be present in question payload
        q = data["question"]
        assert "answer_key" not in q, "SECURITY LEAK: answer_key revealed in recommendation!"
        assert "explanation" not in q, "LEAK: explanation revealed in recommendation!"
        assert "prompt" in q
        assert len(q["options"]) >= 2

    def test_recommend_weak_topic_remediation(self, client: TestClient, test_db: Session):
        """User with low mastery in a practiced topic is targeted for WEAK_TOPIC_REMEDIATION."""
        token = _get_auth_token(client, "struggling_student@example.com")
        headers = {"Authorization": f"Bearer {token}"}

        # Fetch a Python question and submit 2 incorrect attempts to drop mastery to 0%
        py_q1 = test_db.query(Question).filter(Question.topic == "Python").first()
        py_q2 = test_db.query(Question).filter(Question.topic == "Python", Question.id != py_q1.id).first()

        client.post(
            "/api/v1/practice/attempts",
            json={"question_id": py_q1.id, "user_answer": "WRONG"},
            headers=headers,
        )
        client.post(
            "/api/v1/practice/attempts",
            json={"question_id": py_q2.id, "user_answer": "WRONG"},
            headers=headers,
        )

        # Recommendation should now target Python for weak topic remediation
        resp = client.get("/api/v1/practice/recommendations/next-question", headers=headers)
        assert resp.status_code == 200
        data = resp.json()

        # Should target Python for remediation
        assert data["reason_code"] == "WEAK_TOPIC_REMEDIATION"
        assert data["priority_level"] == "high"
        assert data["question"]["topic"] == "Python"
        assert data["topic_mastery_score"] < 60.0
        assert "below the 60% proficiency threshold" in data["rationale"]

    def test_study_plan_generation_structure(self, client: TestClient):
        """GET /api/v1/practice/recommendations/study-plan returns structured curriculum roadmap."""
        token = _get_auth_token(client, "planner_student@example.com")
        headers = {"Authorization": f"Bearer {token}"}

        resp = client.get("/api/v1/practice/recommendations/study-plan", headers=headers)
        assert resp.status_code == 200
        plan = resp.json()

        assert "Junior Python Developer" in plan["target_role"]
        assert "summary" in plan
        assert len(plan["topics"]) >= 5

        # Initial state: all topics unpracticed -> immediate_remediation tier
        for item in plan["topics"]:
            assert item["priority_tier"] in ("immediate_remediation", "consolidation", "maintenance")
            assert item["recommended_questions_count"] >= 1
            assert len(item["action_items"]) >= 2
            assert item["reason_code"] in ("UNPRACTICED_CORE_DOMAIN", "WEAK_TOPIC_REMEDIATION", "CHALLENGE_ADVANCEMENT", "RETENTION_REFRESH")

    def test_recommendation_audits_logged_and_retrieved(self, client: TestClient):
        """Recommendations automatically create audit trail entries queryable by the user."""
        token = _get_auth_token(client, "audit_check_student@example.com")
        headers = {"Authorization": f"Bearer {token}"}

        # Request next question (creates audit)
        client.get("/api/v1/practice/recommendations/next-question", headers=headers)

        # Request study plan (creates audit)
        client.get("/api/v1/practice/recommendations/study-plan", headers=headers)

        # Retrieve audits
        audit_resp = client.get("/api/v1/practice/recommendations/audits", headers=headers)
        assert audit_resp.status_code == 200
        audits = audit_resp.json()

        assert len(audits) >= 2
        types = [a["recommendation_type"] for a in audits]
        assert "next_question" in types
        assert "study_plan" in types

        for a in audits:
            assert len(a["rationale"]) > 5
            assert len(a["reason_code"]) > 2
            assert "created_at" in a

    def test_recommendation_user_isolation(self, client: TestClient):
        """User A and User B audits are completely isolated."""
        token_a = _get_auth_token(client, "student_a_audit@example.com")
        token_b = _get_auth_token(client, "student_b_audit@example.com")

        # User A triggers audit
        client.get("/api/v1/practice/recommendations/next-question", headers={"Authorization": f"Bearer {token_a}"})

        # User B should see 0 audits
        resp_b = client.get("/api/v1/practice/recommendations/audits", headers={"Authorization": f"Bearer {token_b}"})
        assert resp_b.status_code == 200
        assert len(resp_b.json()) == 0

    def test_unauthenticated_recommendations_rejected(self, client: TestClient):
        """Unauthenticated requests to recommendation endpoints return 401."""
        assert client.get("/api/v1/practice/recommendations/next-question").status_code == 401
        assert client.get("/api/v1/practice/recommendations/study-plan").status_code == 401
        assert client.get("/api/v1/practice/recommendations/audits").status_code == 401

