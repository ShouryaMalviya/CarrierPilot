"""Tests for optional semantic similarity adapter, transparent lexical fallback, and engine status."""

import io
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.deps import get_db
from app.db.base import Base
from app.main import app
from app.schemas.matching import DEFAULT_MATCHING_DISCLAIMER
from app.services.semantic_service import (
    MockEmbeddingAdapter,
    SentenceTransformerAdapter,
    semantic_manager,
)


@event.listens_for(Engine, "connect")
def _set_sqlite_pragma(dbapi_connection, connection_record):
    """Enforce foreign key constraints in SQLite test engine."""
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


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


@pytest.fixture(autouse=True)
def cleanup_semantic_provider():
    """Ensure the default semantic provider is restored after every test."""
    yield
    semantic_manager.reset_default_provider()


def _get_auth_token(client: TestClient, email: str) -> str:
    """Helper to register and login a test user, returning their access token."""
    client.post("/api/v1/auth/register", json={"email": email, "password": "SecurePassword123!"})
    res = client.post("/api/v1/auth/login", json={"email": email, "password": "SecurePassword123!"})
    return res.json()["access_token"]


def _create_synthetic_text_pdf(lines: list[str]) -> bytes:
    """Build a minimal valid PDF containing actual extractable text streams."""
    stream_content = "BT\n/F1 12 Tf\n72 712 Td\n"
    for i, line in enumerate(lines):
        if i > 0:
            stream_content += f"0 -18 Td\n({line}) Tj\n"
        else:
            stream_content += f"({line}) Tj\n"
    stream_content += "ET"

    stream_bytes = stream_content.encode("latin-1")
    length = len(stream_bytes)

    pdf = (
        b"%PDF-1.4\n"
        b"1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj\n"
        b"2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj\n"
        b"3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
        b"/Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >> endobj\n"
        b"4 0 obj << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> endobj\n"
        b"5 0 obj << /Length " + str(length).encode("ascii") + b" >>\n"
        b"stream\n" + stream_bytes + b"\nendstream\nendobj\n"
        b"xref\n0 6\n"
        b"0000000000 65535 f \n"
        b"0000000009 00000 n \n"
        b"0000000058 00000 n \n"
        b"0000000115 00000 n \n"
        b"0000000244 00000 n \n"
        b"0000000318 00000 n \n"
        b"trailer << /Size 6 /Root 1 0 R >>\n"
        b"startxref\n450\n%%EOF"
    )
    return pdf


# ==============================================================================
# Unit Tests: Semantic Adapter & Fallback Engine
# ==============================================================================


def test_sentence_transformer_adapter_lazy_state():
    """Adapter begins uninitialized without triggering network requests or model downloads."""
    adapter = SentenceTransformerAdapter("nonexistent-test-model")
    assert adapter.is_available() is False
    assert adapter.get_model_name() == "nonexistent-test-model"


def test_semantic_manager_lexical_fallback():
    """When neural model is unavailable, manager cleanly falls back to deterministic TF-IDF."""
    semantic_manager.reset_default_provider()

    text_a = "Python software engineer with FastAPI and PostgreSQL experience."
    text_b = "Requirements: Python, FastAPI, SQL database."

    sim, mode, is_fallback, reason = semantic_manager.compute_similarity(
        text_a, text_b, prefer_semantic=True
    )

    assert is_fallback is True
    assert mode == "lexical_fallback"
    assert "SentenceTransformer" in reason
    assert sim > 0.0


def test_semantic_manager_explicit_lexical_request():
    """When semantic is not preferred, manager uses pure lexical mode without checking neural model."""
    text_a = "Python developer"
    text_b = "Python backend"

    sim, mode, is_fallback, reason = semantic_manager.compute_similarity(
        text_a, text_b, prefer_semantic=False
    )

    assert mode == "lexical"
    assert is_fallback is True
    assert "explicitly requested" in reason
    assert sim > 0.0


def test_semantic_manager_with_mock_provider():
    """When a neural embedding provider is active, manager returns semantic mode without fallback."""
    mock_provider = MockEmbeddingAdapter(fixed_similarity=0.88, model_name="mock-transformer-v1")
    semantic_manager.set_provider(mock_provider)

    text_a = "Junior Python engineer"
    text_b = "Python engineer"

    sim, mode, is_fallback, reason = semantic_manager.compute_similarity(
        text_a, text_b, prefer_semantic=True
    )

    assert sim == 0.88
    assert mode == "semantic"
    assert is_fallback is False
    assert reason is None
    assert mock_provider.call_count == 1


# ==============================================================================
# API Integration Tests: Semantic Matching & Status
# ==============================================================================


def test_matching_status_endpoint(client: TestClient):
    """GET /api/v1/matching/status reports engine status and fallback transparency."""
    token = _get_auth_token(client, "status_user@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    res = client.get("/api/v1/matching/status", headers=headers)
    assert res.status_code == 200
    data = res.json()

    assert "is_available" in data
    assert "model_name" in data
    assert "fallback_mode" in data
    assert data["fallback_mode"] is True  # default offline environment


def test_match_resume_with_semantic_flag_falls_back(client: TestClient):
    """When use_semantic=True in offline mode, API safely falls back with visible flags."""
    token = _get_auth_token(client, "fallback_user@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    # Upload resume
    pdf_bytes = _create_synthetic_text_pdf(["Technical Skills", "Python, FastAPI, SQL"])
    res_upload = client.post(
        "/api/v1/resumes/upload",
        files={"file": ("cv.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
        headers=headers,
    )
    resume_id = res_upload.json()["id"]

    # Create job
    res_job = client.post(
        "/api/v1/jobs",
        json={"title": "Python Dev", "description": "Requirements: Must know Python and SQL."},
        headers=headers,
    )
    job_id = res_job.json()["id"]

    # Request match with use_semantic=true
    res_match = client.post(
        f"/api/v1/matching/resumes/{resume_id}/jobs/{job_id}?use_semantic=true",
        headers=headers,
    )
    assert res_match.status_code == 200
    data = res_match.json()

    scores = data["scores"]
    assert scores["similarity_mode"] == "lexical_fallback"
    assert scores["is_fallback"] is True
    assert scores["fallback_reason"] is not None
    assert scores["semantic_similarity"] is None
    assert scores["overall_score"] > 0.0
    assert data["disclaimer"] == DEFAULT_MATCHING_DISCLAIMER


def test_match_resume_with_mocked_semantic_provider(client: TestClient):
    """When a neural embedding model is loaded, API produces semantic mode and hybrid score."""
    mock_adapter = MockEmbeddingAdapter(fixed_similarity=0.90)
    semantic_manager.set_provider(mock_adapter)

    token = _get_auth_token(client, "semantic_user@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    pdf_bytes = _create_synthetic_text_pdf(["Technical Skills", "Python, FastAPI, SQL"])
    res_upload = client.post(
        "/api/v1/resumes/upload",
        files={"file": ("cv_sem.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
        headers=headers,
    )
    resume_id = res_upload.json()["id"]

    res_job = client.post(
        "/api/v1/jobs",
        json={
            "title": "Python Developer",
            "description": "Requirements: Must know Python and FastAPI.\nPreferred: Docker.",
        },
        headers=headers,
    )
    job_id = res_job.json()["id"]

    res_match = client.post(
        f"/api/v1/matching/resumes/{resume_id}/jobs/{job_id}?use_semantic=true",
        headers=headers,
    )
    assert res_match.status_code == 200
    data = res_match.json()

    scores = data["scores"]
    assert scores["similarity_mode"] == "semantic"
    assert scores["is_fallback"] is False
    assert scores["fallback_reason"] is None
    assert scores["semantic_similarity"] == 0.90

    # Hybrid weights: 0.50 * 1.0 (req) + 0.30 * 0.90 (sem) + 0.20 * 0.0 (pref) = 0.50 + 0.27 = 0.77 -> 77.0
    expected_score = round((0.50 * 1.0 + 0.30 * 0.90 + 0.20 * 0.0) * 100.0, 2)
    assert scores["overall_score"] == expected_score


def test_batch_match_with_semantic_flag(client: TestClient):
    """Batch match with use_semantic=true propagates fallback indicators across all matches."""
    token = _get_auth_token(client, "batch_sem@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    client.post("/api/v1/jobs/seed-demo", headers=headers)

    pdf_bytes = _create_synthetic_text_pdf(["Technical Skills", "Python, Pandas, SQL"])
    res_upload = client.post(
        "/api/v1/resumes/upload",
        files={"file": ("batch_cv.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
        headers=headers,
    )
    resume_id = res_upload.json()["id"]

    res_batch = client.post(
        f"/api/v1/matching/resumes/{resume_id}/batch?use_semantic=true",
        headers=headers,
    )
    assert res_batch.status_code == 200
    data = res_batch.json()

    for item in data["matches"]:
        assert item["similarity_mode"] == "lexical_fallback"
        assert item["is_fallback"] is True

