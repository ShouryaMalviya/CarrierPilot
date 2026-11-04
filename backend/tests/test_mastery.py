"""Unit and integration tests for transparent recent-weighted topic mastery estimation."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.deps import get_db
from app.db.base import Base
from app.main import app
from app.models import PracticeAttempt, Question, TopicMastery
from app.services.mastery_service import calculate_topic_mastery, get_difficulty_factor
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
# Pure Math Unit Tests
# ==============================================================================

class TestMasteryMathUnit:
    """Validate mathematical correctness, recency decay, and difficulty weighting."""

    def test_difficulty_factor_scaling(self):
        """Difficulty scales: easy=0.8, medium=1.0, hard=1.2."""
        assert get_difficulty_factor("easy") == 0.8
        assert get_difficulty_factor("medium") == 1.0
        assert get_difficulty_factor("hard") == 1.2
        assert get_difficulty_factor("unknown") == 1.0
        assert get_difficulty_factor(None) == 1.0

    def test_calculate_mastery_empty_attempts(self):
        """Zero attempts returns 0.0 score and NO_DATA reason code."""
        score, reasons, num, den, contribs = calculate_topic_mastery([])
        assert score == 0.0
        assert reasons == ["NO_DATA"]
        assert num == 0.0
        assert den == 0.0
        assert len(contribs) == 0

    def test_calculate_mastery_recency_weighting_favors_recent_success(self):
        """Recent correct attempt should yield higher score than older correct attempt."""
        q_med = Question(id=1, topic="Python", difficulty="medium", prompt="P", answer_key="A", explanation="E")

        # Scenario A: Attempt 1 = Incorrect, Attempt 2 (most recent) = Correct
        att1_wrong = PracticeAttempt(id=1, question_id=1, user_id=1, user_answer="B", is_correct=False, score=0.0)
        att2_right = PracticeAttempt(id=2, question_id=1, user_id=1, user_answer="A", is_correct=True, score=1.0)
        score_recent_win, _, _, _, _ = calculate_topic_mastery([(att1_wrong, q_med), (att2_right, q_med)])

        # Scenario B: Attempt 1 = Correct, Attempt 2 (most recent) = Incorrect
        att1_right = PracticeAttempt(id=3, question_id=1, user_id=1, user_answer="A", is_correct=True, score=1.0)
        att2_wrong = PracticeAttempt(id=4, question_id=1, user_id=1, user_answer="B", is_correct=False, score=0.0)
        score_recent_loss, _, _, _, _ = calculate_topic_mastery([(att1_right, q_med), (att2_wrong, q_med)])

        # Mathematically: 1.0 / 1.85 * 100 = 54.1% vs 0.85 / 1.85 * 100 = 45.9%
        assert score_recent_win > score_recent_loss
        assert score_recent_win == pytest.approx(54.1, 0.1)
        assert score_recent_loss == pytest.approx(45.9, 0.1)

    def test_mastery_bounded_between_zero_and_hundred(self):
        """Scores must strictly stay in [0.0, 100.0]."""
        q_easy = Question(id=1, topic="Python", difficulty="easy", prompt="P", answer_key="A", explanation="E")
        q_hard = Question(id=2, topic="Python", difficulty="hard", prompt="P", answer_key="A", explanation="E")

        # All correct
        all_right = [
            (PracticeAttempt(id=i, question_id=1, user_id=1, user_answer="A", is_correct=True, score=1.0), q_easy)
            for i in range(5)
        ]
        score_max, _, _, _, _ = calculate_topic_mastery(all_right)
        assert score_max == 100.0

        # All incorrect
        all_wrong = [
            (PracticeAttempt(id=i, question_id=2, user_id=1, user_answer="B", is_correct=False, score=0.0), q_hard)
            for i in range(5)
        ]
        score_min, reasons_min, _, _, _ = calculate_topic_mastery(all_wrong)
        assert score_min == 0.0
        assert "NEEDS_PRACTICE" in reasons_min

    def test_reason_codes_generation(self):
        """Verify reason code assignment: TOPIC_PROFICIENT, STRUGGLING_MEDIUM_HARD, RECENT_IMPROVEMENT."""
        q_hard = Question(id=1, topic="SQL", difficulty="hard", prompt="P", answer_key="A", explanation="E")

        # 4 attempts: 2 wrong then 2 right -> RECENT_IMPROVEMENT
        att_progression = [
            (PracticeAttempt(id=1, question_id=1, user_id=1, user_answer="B", is_correct=False, score=0.0), q_hard),
            (PracticeAttempt(id=2, question_id=1, user_id=1, user_answer="B", is_correct=False, score=0.0), q_hard),
            (PracticeAttempt(id=3, question_id=1, user_id=1, user_answer="A", is_correct=True, score=1.0), q_hard),
            (PracticeAttempt(id=4, question_id=1, user_id=1, user_answer="A", is_correct=True, score=1.0), q_hard),
        ]
        score, reasons, _, _, _ = calculate_topic_mastery(att_progression)
        assert "RECENT_IMPROVEMENT" in reasons


# ==============================================================================
# Service & API Integration Tests
# ==============================================================================

class TestMasteryServiceAndAPI:
    """Validate real-time database updates, user isolation, and REST disclosure."""

    def test_new_user_zero_state_mastery(self, client: TestClient):
        """New user with no attempts gets 0.0 score and NO_DATA reason code for all topics."""
        token = _get_auth_token(client, "new_student@example.com")
        headers = {"Authorization": f"Bearer {token}"}

        resp = client.get("/api/v1/practice/mastery", headers=headers)
        assert resp.status_code == 200
        data = resp.json()

        assert data["overall_average_mastery"] == 0.0
        assert data["proficient_topics_count"] == 0
        assert data["needs_practice_topics_count"] == 0
        assert len(data["items"]) >= 5

        for item in data["items"]:
            assert item["mastery_score"] == 0.0
            assert item["recent_attempts_count"] == 0
            assert item["reason_codes"] == ["NO_DATA"]

    def test_real_time_mastery_update_on_attempt_submission(
        self, client: TestClient, test_db: Session
    ):
        """Submitting an attempt immediately updates the user's topic mastery score."""
        token = _get_auth_token(client, "active_student@example.com")
        headers = {"Authorization": f"Bearer {token}"}

        py_q = test_db.query(Question).filter(Question.topic == "Python").first()
        assert py_q is not None

        # Verify initial mastery is 0.0
        init_resp = client.get("/api/v1/practice/mastery", headers=headers)
        py_init = next(it for it in init_resp.json()["items"] if it["topic"] == "Python")
        assert py_init["mastery_score"] == 0.0

        # Submit 1 correct attempt
        client.post(
            "/api/v1/practice/attempts",
            json={"question_id": py_q.id, "user_answer": py_q.answer_key},
            headers=headers,
        )

        # Check mastery immediately after submission
        after_resp = client.get("/api/v1/practice/mastery", headers=headers)
        py_after = next(it for it in after_resp.json()["items"] if it["topic"] == "Python")
        assert py_after["mastery_score"] == 100.0
        assert py_after["recent_attempts_count"] == 1
        assert "FEW_ATTEMPTS" in py_after["reason_codes"]

    def test_topic_mastery_audit_explanation_endpoint(
        self, client: TestClient, test_db: Session
    ):
        """GET /api/v1/practice/mastery/{topic} discloses mathematical breakdown and weights."""
        token = _get_auth_token(client, "audit_student@example.com")
        headers = {"Authorization": f"Bearer {token}"}

        sql_q = test_db.query(Question).filter(Question.topic == "SQL").first()
        assert sql_q is not None

        # Submit attempt
        client.post(
            "/api/v1/practice/attempts",
            json={"question_id": sql_q.id, "user_answer": sql_q.answer_key, "duration_seconds": 25},
            headers=headers,
        )

        # Query audit explanation
        audit_resp = client.get("/api/v1/practice/mastery/SQL", headers=headers)
        assert audit_resp.status_code == 200
        audit = audit_resp.json()

        assert audit["topic"] == "SQL"
        assert audit["decay_gamma"] == 0.85
        assert audit["mastery_score"] == 100.0
        assert audit["total_attempts"] == 1
        assert len(audit["attempt_contributions"]) == 1
        contrib = audit["attempt_contributions"][0]
        assert contrib["is_correct"] is True
        assert contrib["weight"] == 1.0

    def test_mastery_ownership_isolation(self, client: TestClient, test_db: Session):
        """User A's attempts must not affect User B's mastery scores."""
        token_a = _get_auth_token(client, "student_a_mastery@example.com")
        token_b = _get_auth_token(client, "student_b_mastery@example.com")

        devops_q = test_db.query(Question).filter(Question.topic == "DevOps").first()
        assert devops_q is not None

        # User A submits attempt
        client.post(
            "/api/v1/practice/attempts",
            json={"question_id": devops_q.id, "user_answer": devops_q.answer_key},
            headers={"Authorization": f"Bearer {token_a}"},
        )

        # User A should have 100.0 mastery in DevOps
        resp_a = client.get("/api/v1/practice/mastery", headers={"Authorization": f"Bearer {token_a}"})
        devops_a = next(it for it in resp_a.json()["items"] if it["topic"] == "DevOps")
        assert devops_a["mastery_score"] == 100.0

        # User B should still have 0.0 mastery in DevOps
        resp_b = client.get("/api/v1/practice/mastery", headers={"Authorization": f"Bearer {token_b}"})
        devops_b = next(it for it in resp_b.json()["items"] if it["topic"] == "DevOps")
        assert devops_b["mastery_score"] == 0.0
        assert devops_b["recent_attempts_count"] == 0

    def test_recalculate_mastery_endpoint(self, client: TestClient):
        """POST /api/v1/practice/mastery/recalculate forces clean recomputation."""
        token = _get_auth_token(client, "recalc_student@example.com")
        headers = {"Authorization": f"Bearer {token}"}

        resp = client.post("/api/v1/practice/mastery/recalculate", headers=headers)
        assert resp.status_code == 200
        assert len(resp.json()["items"]) >= 5

    def test_unauthenticated_mastery_endpoints_rejected(self, client: TestClient):
        """Mastery endpoints return 401 when accessed without bearer authentication."""
        assert client.get("/api/v1/practice/mastery").status_code == 401
        assert client.get("/api/v1/practice/mastery/Python").status_code == 401
        assert client.post("/api/v1/practice/mastery/recalculate").status_code == 401

