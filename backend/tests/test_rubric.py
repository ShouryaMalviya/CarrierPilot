"""Tests for Part 24 - 5-dimension rubric-based coaching feedback engine and endpoints."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.deps import get_db
from app.db.base import Base
from app.main import app
from app.schemas.rubric import RubricFeedback
from app.services.rubric_service import (
    evaluate_completeness,
    evaluate_relevance,
    evaluate_response,
    evaluate_structure,
    evaluate_technical_correctness,
    evaluate_use_of_examples,
    extract_sentences,
)


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
# Unit Tests: 5-Dimension Rubric Scoring Engine
# ==============================================================================

class TestRubricDimensionEvaluators:
    """Validate each of the five rubric evaluation dimensions individually."""

    SAMPLE_QUESTION = (
        "Design a web-based collaborative document editor (similar to Google Docs) where multiple users "
        "can concurrently edit documents with low latency. Describe your client-server communication protocol, "
        "synchronization strategy (e.g., CRDT vs. Operational Transformation), state persistence, and how you "
        "handle network disconnects and offline edits."
    )

    SAMPLE_KEY_CONCEPTS = [
        "WebSockets",
        "Operational Transformation (OT)",
        "Conflict-free Replicated Data Types (CRDT)",
        "Document Snapshotting",
        "Optimistic UI Updates",
        "Disconnection Recovery",
    ]

    HIGH_QUALITY_ANSWER = (
        "Architecture Overview:\n"
        "To build a real-time collaborative document editor, I would use Conflict-Free Replicated Data Types (CRDT) "
        "implemented via the Yjs library. Clients communicate with an autoscaled cluster of Node.js servers via WebSockets.\n\n"
        "1. Concurrency and Synchronization:\n"
        "Every client maintains an in-memory document state with optimistic UI updates. When a keystroke occurs, "
        "a binary update chunk with a lamport timestamp is generated and broadcast over the WebSocket connection. "
        "CRDTs guarantee strong eventual consistency without requiring a central serialization lock.\n\n"
        "2. State Persistence & Snapshots:\n"
        "Redis stores the active ephemeral document rooms, while snapshots are persisted to PostgreSQL and AWS S3 "
        "every 30 seconds or after 1,000 edits. This keeps WebSocket reconnection fast.\n\n"
        "3. Network Disconnects & Edge Cases:\n"
        "If a network disconnect occurs, edits are buffered locally in IndexedDB. Upon reconnection, buffered delta updates "
        "are transmitted and merged automatically. If a partition lasts over 10 minutes, the client requests a full snapshot. "
        "We maintain sub-50ms sync latency across 99.9% of sessions."
    )

    OFF_TOPIC_ANSWER = (
        "In cooking, making a chocolate cake requires high quality cocoa powder, organic flour, and unsalted butter. "
        "First, you preheat the oven to 350 degrees Fahrenheit. Mix the dry ingredients thoroughly before whisking in the milk."
    )

    def test_relevance_high_vs_off_topic(self):
        """Relevance evaluator awards high points to aligned answers and low points to off-topic text."""
        sentences_good = extract_sentences(self.HIGH_QUALITY_ANSWER)
        rel_good = evaluate_relevance(
            self.SAMPLE_QUESTION, self.HIGH_QUALITY_ANSWER, "Full-Stack Engineer", "System Design", sentences_good
        )
        assert rel_good.score >= 14.0
        assert rel_good.score <= 20.0
        assert len(rel_good.positive_evidence) >= 1

        sentences_bad = extract_sentences(self.OFF_TOPIC_ANSWER)
        rel_bad = evaluate_relevance(
            self.SAMPLE_QUESTION, self.OFF_TOPIC_ANSWER, "Full-Stack Engineer", "System Design", sentences_bad
        )
        assert rel_bad.score < 8.0

    def test_technical_correctness_precision(self):
        """Technical correctness evaluates presence and contextual usage of domain terminology."""
        sentences_good = extract_sentences(self.HIGH_QUALITY_ANSWER)
        tc_good = evaluate_technical_correctness(self.HIGH_QUALITY_ANSWER, sentences_good)
        assert tc_good.score >= 16.0
        assert tc_good.score <= 20.0
        assert "crdt" in tc_good.feedback.lower() or "technical precision" in tc_good.feedback.lower()

        sentences_bad = extract_sentences("I will write some code and make it fast and nice using computers.")
        tc_bad = evaluate_technical_correctness("I will write some code and make it fast and nice using computers.", sentences_bad)
        assert tc_bad.score <= 10.0

    def test_completeness_tracks_covered_and_missed_concepts(self):
        """Completeness partitions expected key concepts into covered vs missed and checks edge cases."""
        sentences = extract_sentences(self.HIGH_QUALITY_ANSWER)
        comp, covered, missed = evaluate_completeness(
            self.HIGH_QUALITY_ANSWER, self.SAMPLE_KEY_CONCEPTS, sentences
        )

        assert comp.score >= 14.0
        assert comp.score <= 20.0
        assert "WebSockets" in covered or "WebSockets" in [c for c in covered if "websocket" in c.lower()]
        assert "Conflict-free Replicated Data Types (CRDT)" in covered

        # Partial answer with zero edge cases and few concepts
        partial_text = "I would just use WebSockets to send data to the server."
        p_sentences = extract_sentences(partial_text)
        p_comp, p_covered, p_missed = evaluate_completeness(partial_text, self.SAMPLE_KEY_CONCEPTS, p_sentences)
        assert p_comp.score < 10.0
        assert len(p_missed) >= 3

    def test_structure_detects_paragraphs_lists_and_transitions(self):
        """Structure evaluates paragraphing, numbered list markers, and structural headers."""
        sentences = extract_sentences(self.HIGH_QUALITY_ANSWER)
        struct = evaluate_structure(self.HIGH_QUALITY_ANSWER, "System Design", sentences)
        assert struct.score >= 15.0
        assert struct.score <= 20.0

        # Run-on unformatted sentence blob
        wall_of_text = (
            "you just open a websocket and you send the data and then if it fails you retry and then you "
            "save it to a database and everyone can see it and that is how it works."
        )
        w_sentences = extract_sentences(wall_of_text)
        w_struct = evaluate_structure(wall_of_text, "System Design", w_sentences)
        assert w_struct.score <= 10.0

    def test_structure_behavioral_star_method(self):
        """Structure evaluator rewards STAR method in behavioral interview questions."""
        behavioral_answer = (
            "Situation:\n"
            "In my previous project, technical debt in our billing service led to high error rates during end-of-month processing.\n\n"
            "Task:\n"
            "As the tech lead, my task was to remediate the service without halting active subscription renewals.\n\n"
            "Action:\n"
            "I isolated the bottleneck using APM traces, introduced idempotent payment retry queues with exponential backoff, "
            "and established automated integration tests.\n\n"
            "Result:\n"
            "Our error rate dropped by 98% and billing processing time decreased from 45 minutes to 3 minutes."
        )
        sentences = extract_sentences(behavioral_answer)
        struct = evaluate_structure(behavioral_answer, "Behavioral & Leadership", sentences)
        assert struct.score >= 16.0

    def test_use_of_examples_detects_tools_metrics_and_code(self):
        """Use of examples identifies concrete named systems, quantitative SLAs, and code patterns."""
        sentences = extract_sentences(self.HIGH_QUALITY_ANSWER)
        ex = evaluate_use_of_examples(self.HIGH_QUALITY_ANSWER, sentences)
        assert ex.score >= 14.0
        assert ex.score <= 20.0

        abstract_text = (
            "We should choose good tools and ensure everything performs nicely under normal operational loads "
            "by picking the right components."
        )
        a_sentences = extract_sentences(abstract_text)
        a_ex = evaluate_use_of_examples(abstract_text, a_sentences)
        assert a_ex.score <= 8.0

    def test_evaluate_response_composite_bounds_and_disclaimer(self):
        """Composite evaluation returns full RubricFeedback with scores strictly bounded in [0, 100]."""
        feedback = evaluate_response(
            question_text=self.SAMPLE_QUESTION,
            user_response=self.HIGH_QUALITY_ANSWER,
            role="Full-Stack Engineer",
            competency="System Design",
            key_concepts=self.SAMPLE_KEY_CONCEPTS,
        )

        assert isinstance(feedback, RubricFeedback)
        assert 0.0 <= feedback.total_score <= 100.0
        assert feedback.total_score >= 70.0  # High quality answer should achieve a strong score

        for dim_name, dim_score in feedback.dimension_scores.items():
            assert 0.0 <= dim_score.score <= 20.0
            assert dim_score.max_score == 20.0
            assert len(dim_score.positive_evidence) >= 1

        assert len(feedback.positive_highlights) >= 1
        assert len(feedback.actionable_improvements) >= 1
        assert "predict" in feedback.disclaimer.lower() or "ethical" in feedback.disclaimer.lower()

    def test_evidence_quotes_are_verbatim_subsets(self):
        """Positive evidence snippets extracted by the rubric engine are verbatim substrings of the response."""
        feedback = evaluate_response(
            question_text=self.SAMPLE_QUESTION,
            user_response=self.HIGH_QUALITY_ANSWER,
            key_concepts=self.SAMPLE_KEY_CONCEPTS,
        )

        normalized_answer = " ".join(self.HIGH_QUALITY_ANSWER.split()).lower()
        for dim_score in feedback.dimension_scores.values():
            for quote in dim_score.positive_evidence:
                # Remove ellipsis from quote if trimmed
                clean_quote = quote.rstrip(".").strip()
                assert clean_quote.lower() in normalized_answer


# ==============================================================================
# Integration Tests: Interview Feedback API
# ==============================================================================

class TestRubricFeedbackAPI:
    """Validate end-to-end response submission and feedback retrieval endpoints."""

    def test_submit_triggers_rubric_evaluation(self, client: TestClient):
        """Submitting a response evaluates it against the 5-dimension rubric and records scores."""
        token = _get_auth_token(client, "rubric_candidate_1@example.com")
        headers = {"Authorization": f"Bearer {token}"}

        # Create session
        create_resp = client.post(
            "/api/v1/interviews/sessions",
            json={"role": "Backend Engineer", "competency": "System Design"},
            headers=headers,
        )
        assert create_resp.status_code == 201
        session_id = create_resp.json()["id"]

        written_response = (
            "To design a high-throughput distributed notification engine, I would decouple ingestion "
            "from delivery using Apache Kafka as a persistent message broker. Ingestion API pods validate payloads "
            "and assign an idempotency key before publishing to a partition keyed by user_id.\n\n"
            "Worker pools consume from Kafka topics and route messages to SMS (Twilio), Push (APNS/FCM), or Email (SendGrid). "
            "Each worker implements a Token Bucket rate limiter to respect provider rate limits and an exponential backoff "
            "retry policy with a Dead Letter Queue (DLQ) after 5 failed attempts.\n\n"
            "State persistence uses Redis for deduplication with a 24-hour TTL, and PostgreSQL records delivery audits. "
            "The system delivers sub-200ms latency at 10,000 requests per second."
        )

        # Submit response
        submit_resp = client.post(
            f"/api/v1/interviews/sessions/{session_id}/submit",
            json={"user_response": written_response, "duration_seconds": 240},
            headers=headers,
        )
        assert submit_resp.status_code == 200
        data = submit_resp.json()

        assert data["status"] == "completed"
        assert data["total_score"] is not None
        assert data["total_score"] >= 65.0
        assert data["dimension_scores"] is not None
        assert "relevance" in data["dimension_scores"]
        assert "technical_correctness" in data["dimension_scores"]
        assert "completeness" in data["dimension_scores"]
        assert "structure" in data["dimension_scores"]
        assert "use_of_examples" in data["dimension_scores"]

    def test_get_session_feedback_endpoint(self, client: TestClient):
        """GET /sessions/{id}/feedback returns full RubricFeedback model."""
        token = _get_auth_token(client, "rubric_candidate_2@example.com")
        headers = {"Authorization": f"Bearer {token}"}

        create_resp = client.post("/api/v1/interviews/sessions", json={}, headers=headers)
        session_id = create_resp.json()["id"]

        client.post(
            f"/api/v1/interviews/sessions/{session_id}/submit",
            json={
                "user_response": (
                    "I would implement Conflict-Free Replicated Data Types (CRDTs) with WebSockets to synchronize "
                    "document character inserts across clients. Periodic snapshots are stored in PostgreSQL every 30 seconds. "
                    "Offline updates are cached in IndexedDB and re-synced upon reconnection with sub-50ms latency."
                )
            },
            headers=headers,
        )

        feedback_resp = client.get(f"/api/v1/interviews/sessions/{session_id}/feedback", headers=headers)
        assert feedback_resp.status_code == 200
        feedback = feedback_resp.json()

        assert "rubric_version" in feedback
        assert "total_score" in feedback
        assert "dimension_scores" in feedback
        assert "positive_highlights" in feedback
        assert "actionable_improvements" in feedback
        assert "summary" in feedback
        assert "disclaimer" in feedback
        assert "predict" in feedback["disclaimer"].lower() or "ethical" in feedback["disclaimer"].lower()

    def test_get_feedback_on_in_progress_session_rejected(self, client: TestClient):
        """Requesting feedback for an in-progress session before submission returns 400."""
        token = _get_auth_token(client, "rubric_candidate_3@example.com")
        headers = {"Authorization": f"Bearer {token}"}

        create_resp = client.post("/api/v1/interviews/sessions", json={}, headers=headers)
        session_id = create_resp.json()["id"]

        resp = client.get(f"/api/v1/interviews/sessions/{session_id}/feedback", headers=headers)
        assert resp.status_code == 400

    def test_get_feedback_on_abandoned_session_rejected(self, client: TestClient):
        """Requesting feedback for an abandoned session returns 400."""
        token = _get_auth_token(client, "rubric_candidate_4@example.com")
        headers = {"Authorization": f"Bearer {token}"}

        create_resp = client.post("/api/v1/interviews/sessions", json={}, headers=headers)
        session_id = create_resp.json()["id"]

        client.post(f"/api/v1/interviews/sessions/{session_id}/abandon", headers=headers)

        resp = client.get(f"/api/v1/interviews/sessions/{session_id}/feedback", headers=headers)
        assert resp.status_code == 400

    def test_feedback_ownership_isolation(self, client: TestClient):
        """User B cannot access feedback for User A's interview session (404 isolation)."""
        token_a = _get_auth_token(client, "rubric_user_a@example.com")
        token_b = _get_auth_token(client, "rubric_user_b@example.com")

        headers_a = {"Authorization": f"Bearer {token_a}"}
        headers_b = {"Authorization": f"Bearer {token_b}"}

        create_resp = client.post("/api/v1/interviews/sessions", json={}, headers=headers_a)
        session_id = create_resp.json()["id"]

        client.post(
            f"/api/v1/interviews/sessions/{session_id}/submit",
            json={
                "user_response": (
                    "This is a detailed answer describing database indexing and replication topologies "
                    "with Redis caching and connection pooling."
                )
            },
            headers=headers_a,
        )

        # User B attempts to access User A's feedback
        resp = client.get(f"/api/v1/interviews/sessions/{session_id}/feedback", headers=headers_b)
        assert resp.status_code == 404
