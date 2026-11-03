"""Unit and API tests for the question bank, curated seed content, and topic taxonomy."""

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.deps import get_db
from app.db.base import Base
from app.main import app
from app.models import Question, User
from app.schemas.question import QuestionCreate, QuestionOption
from app.services import question_service


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


# ==============================================================================
# Schema Validation Unit Tests
# ==============================================================================

class TestQuestionSchemas:
    """Validate Pydantic question schema constraints and answer key integrity."""

    def test_valid_question_schema(self):
        """Valid question data with matching answer key passes validation."""
        q_data = QuestionCreate(
            topic="Python",
            difficulty="easy",
            question_type="mcq",
            prompt="What is the result of type(lambda: None)?",
            options=[
                QuestionOption(id="A", text="<class 'function'>"),
                QuestionOption(id="B", text="<class 'lambda'>"),
                QuestionOption(id="C", text="<class 'object'>"),
                QuestionOption(id="D", text="<class 'builtin_function'>"),
            ],
            answer_key="A",
            explanation="In Python, lambda expressions construct standard function objects.",
        )
        assert q_data.answer_key == "A"
        assert len(q_data.options) == 4

    def test_answer_key_must_match_existing_option(self):
        """Answer key not present in option IDs raises validation error."""
        with pytest.raises(ValidationError) as exc_info:
            QuestionCreate(
                topic="SQL",
                difficulty="medium",
                question_type="mcq",
                prompt="Which keyword sorts records in descending order?",
                options=[
                    QuestionOption(id="A", text="ASC"),
                    QuestionOption(id="B", text="DESC"),
                ],
                answer_key="Z",  # Invalid ID
                explanation="DESC sorts in descending order.",
            )
        assert "answer_key 'Z' must correspond to one of the option IDs" in str(exc_info.value)

    def test_duplicate_option_ids_rejected(self):
        """Duplicate option IDs are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            QuestionCreate(
                topic="DevOps",
                difficulty="easy",
                question_type="mcq",
                prompt="Which tool manages Linux packages on Debian?",
                options=[
                    QuestionOption(id="A", text="apt"),
                    QuestionOption(id="A", text="yum"),  # Duplicate ID 'A'
                ],
                answer_key="A",
                explanation="apt is used on Debian systems.",
            )
        assert "All question option IDs must be unique" in str(exc_info.value)

    def test_short_prompt_rejected(self):
        """Prompts shorter than 10 characters are rejected."""
        with pytest.raises(ValidationError):
            QuestionCreate(
                topic="Web",
                difficulty="easy",
                question_type="mcq",
                prompt="Too short",
                options=[
                    QuestionOption(id="A", text="Option 1"),
                    QuestionOption(id="B", text="Option 2"),
                ],
                answer_key="A",
                explanation="Explanation for the question.",
            )


# ==============================================================================
# Service Logic & Seeding Tests
# ==============================================================================

class TestQuestionService:
    """Validate database operations, idempotency, and topic taxonomy."""

    def test_seed_questions_idempotent(self, test_db: Session):
        """Seeding populated questions must succeed and be idempotent on second run."""
        seeded_1, total_1 = question_service.seed_questions(test_db, force_reset=False)
        assert seeded_1 >= 25
        assert total_1 >= 25

        # Re-running without force_reset should add 0 new questions
        seeded_2, total_2 = question_service.seed_questions(test_db, force_reset=False)
        assert seeded_2 == 0
        assert total_2 == total_1

    def test_topic_summaries_coverage(self, test_db: Session):
        """Topic summaries must cover the 5 core domains with difficulty distribution."""
        question_service.seed_questions(test_db, force_reset=False)
        summaries = question_service.get_topic_summaries(test_db)

        topics = {s.topic for s in summaries}
        expected_domains = {"Python", "Data Structures", "SQL", "Web Development", "DevOps"}
        assert expected_domains.issubset(topics), f"Missing domains: {expected_domains - topics}"

        for s in summaries:
            assert s.total_questions > 0
            assert s.easy_count + s.medium_count + s.hard_count == s.total_questions

    def test_list_questions_filters(self, test_db: Session):
        """Filtering by topic and difficulty must return exact subsets."""
        question_service.seed_questions(test_db, force_reset=False)

        python_questions, total_py = question_service.list_questions(test_db, topic="Python")
        assert total_py >= 5
        assert all(q.topic == "Python" for q in python_questions)

        hard_sql, total_hard_sql = question_service.list_questions(
            test_db, topic="SQL", difficulty="hard"
        )
        assert total_hard_sql >= 1
        assert all(q.topic == "SQL" and q.difficulty == "hard" for q in hard_sql)


# ==============================================================================
# API Endpoint Tests
# ==============================================================================

class TestQuestionAPI:
    """Validate HTTP REST contract, authentication guards, and answer leakage prevention."""

    def test_api_seed_endpoint(self, client: TestClient):
        """POST /api/v1/practice/seed initializes or updates question bank."""
        resp = client.post("/api/v1/practice/seed")
        assert resp.status_code == 200
        data = resp.json()
        assert "seeded_count" in data
        assert "total_count" in data
        assert data["total_count"] >= 25

    def test_api_get_topics(self, client: TestClient):
        """GET /api/v1/practice/topics returns available topic summaries."""
        resp = client.get("/api/v1/practice/topics")
        assert resp.status_code == 200
        topics = resp.json()
        assert len(topics) >= 5
        topic_names = [t["topic"] for t in topics]
        assert "Python" in topic_names
        assert "Data Structures" in topic_names

    def test_api_list_questions_prevents_answer_leakage(self, client: TestClient):
        """GET /api/v1/practice/questions must NOT leak answer_key or explanation."""
        resp = client.get("/api/v1/practice/questions?limit=10")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 25
        assert len(data["items"]) <= 10

        for item in data["items"]:
            # Critical security & grading integrity check:
            assert "answer_key" not in item, "SECURITY LEAK: answer_key found in public question list!"
            assert "explanation" not in item, "LEAK: explanation found in public question list!"
            assert "prompt" in item
            assert "options" in item
            assert len(item["options"]) >= 2

    def test_api_get_single_question_public(self, client: TestClient):
        """GET /api/v1/practice/questions/{id} returns single public question without answers."""
        list_resp = client.get("/api/v1/practice/questions?limit=1")
        first_q = list_resp.json()["items"][0]
        q_id = first_q["id"]

        resp = client.get(f"/api/v1/practice/questions/{q_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == q_id
        assert "answer_key" not in data, "SECURITY LEAK: answer_key present in public question view!"
        assert "explanation" not in data, "LEAK: explanation present in public question view!"

    def test_api_get_nonexistent_question_404(self, client: TestClient):
        """GET /api/v1/practice/questions/999999 returns 404."""
        resp = client.get("/api/v1/practice/questions/999999")
        assert resp.status_code == 404

    def test_api_authenticated_detail_and_create(
        self, client: TestClient, test_db: Session
    ):
        """Authenticated user can author a question and inspect full details with answers."""
        # Register and login a test user
        client.post(
            "/api/v1/auth/register",
            json={
                "email": "author_tester@example.com",
                "password": "StrongPassword123!",
            },
        )
        login_resp = client.post(
            "/api/v1/auth/login",
            json={
                "email": "author_tester@example.com",
                "password": "StrongPassword123!",
            },
        )
        assert login_resp.status_code == 200
        token = login_resp.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Create a new custom question
        create_payload = {
            "topic": "Algorithms",
            "difficulty": "medium",
            "question_type": "mcq",
            "prompt": "What is the worst-case time complexity of QuickSort?",
            "options": [
                {"id": "A", "text": "O(N log N)"},
                {"id": "B", "text": "O(N^2)"},
                {"id": "C", "text": "O(N)"},
                {"id": "D", "text": "O(log N)"},
            ],
            "answer_key": "B",
            "explanation": "QuickSort degrades to O(N^2) worst-case when unbalanced pivots are repeatedly selected.",
            "rubric_version": "1.0.0",
            "is_synthetic": False,
            "is_active": True,
        }

        # Unauthenticated create should fail
        unauth_resp = client.post("/api/v1/practice/questions", json=create_payload)
        assert unauth_resp.status_code == 401

        # Authenticated create should succeed
        auth_resp = client.post(
            "/api/v1/practice/questions",
            json=create_payload,
            headers=headers,
        )
        assert auth_resp.status_code == 201
        new_q = auth_resp.json()
        assert new_q["answer_key"] == "B"
        assert new_q["topic"] == "Algorithms"

        # Detail endpoint reveals answer key to authenticated caller
        detail_resp = client.get(
            f"/api/v1/practice/questions/{new_q['id']}/detail",
            headers=headers,
        )
        assert detail_resp.status_code == 200
        detail_data = detail_resp.json()
        assert detail_data["answer_key"] == "B"
        assert "degrades to O(N^2)" in detail_data["explanation"]
