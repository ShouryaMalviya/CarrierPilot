"""Tests for Part 15: Hybrid scoring, explainable evidence citing, and learning recommendations."""

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
from app.services.semantic_service import MockEmbeddingAdapter, semantic_manager


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
# Tests for Part 15: Hybrid Ranking & Explainable Evidence
# ==============================================================================


def test_hybrid_match_with_evidence_and_recommendations(client: TestClient):
    """Verify evidence snippet citing and prioritized learning recommendations."""
    token = _get_auth_token(client, "hybrid_user@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Upload candidate resume
    lines = [
        "Professional Summary",
        "Junior Python developer building web backends.",
        "Technical Skills",
        "Python, FastAPI, SQL",
    ]
    pdf_bytes = _create_synthetic_text_pdf(lines)
    upload_res = client.post(
        "/api/v1/resumes/upload",
        files={"file": ("hybrid_cv.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
        headers=headers,
    )
    assert upload_res.status_code == 201
    resume_id = upload_res.json()["id"]

    # 2. Create job with required skills (Python, FastAPI, Docker) and preferred skill (Kubernetes)
    job_res = client.post(
        "/api/v1/jobs",
        json={
            "title": "Backend Cloud Engineer",
            "company": "CloudScale Inc",
            "description": (
                "Job Overview:\n"
                "We need a backend developer.\n\n"
                "Requirements:\n"
                "Strong experience in Python, FastAPI, and Docker.\n\n"
                "Preferred Qualifications:\n"
                "Experience with Kubernetes is desirable."
            ),
        },
        headers=headers,
    )
    assert job_res.status_code == 201
    job_id = job_res.json()["id"]

    # 3. Match resume with job
    res = client.post(f"/api/v1/matching/resumes/{resume_id}/jobs/{job_id}", headers=headers)
    assert res.status_code == 200
    data = res.json()

    # 4. Check applied weights (lexical fallback mode)
    scores = data["scores"]
    assert "applied_weights" in scores
    assert scores["applied_weights"]["required_skills"] == 0.60
    assert scores["applied_weights"]["preferred_skills"] == 0.20
    assert scores["applied_weights"]["tfidf_similarity"] == 0.20

    # 5. Check evidence citations
    evidence = data["evidence"]
    assert len(evidence) >= 2
    matched_names = {e["canonical_name"] for e in evidence}
    assert "Python" in matched_names
    assert "FastAPI" in matched_names
    for item in evidence:
        assert item["is_required"] is True
        assert item["evidence_snippet"] is not None

    # 6. Check learning recommendations
    recs = data["recommendations"]
    assert len(recs) >= 2

    # High-priority recommendation for missing required Docker
    docker_rec = next((r for r in recs if r["skill_name"] == "Docker"), None)
    assert docker_rec is not None
    assert docker_rec["priority"] == "high"
    assert "explicitly required" in docker_rec["rationale"]
    assert "Docker" in docker_rec["suggested_action"]

    # Medium-priority recommendation for missing preferred Kubernetes
    k8s_rec = next((r for r in recs if r["skill_name"] == "Kubernetes"), None)
    assert k8s_rec is not None
    assert k8s_rec["priority"] == "medium"
    assert "preferred or bonus" in k8s_rec["rationale"]

    # 7. Check explanation summary
    summary = data["explanation_summary"]
    assert "Backend Cloud Engineer" in summary
    assert "covers 2 of 3 required skills" in summary
    assert "Missing required qualifications: Docker" in summary
    assert "Overall match score is" in summary

    # 8. Check disclaimer
    assert data["disclaimer"] == DEFAULT_MATCHING_DISCLAIMER


def test_hybrid_match_with_semantic_provider_weights(client: TestClient):
    """When semantic neural embeddings are active, hybrid weights (0.50/0.30/0.20) are applied."""
    mock_provider = MockEmbeddingAdapter(fixed_similarity=0.80)
    semantic_manager.set_provider(mock_provider)

    token = _get_auth_token(client, "sem_weights@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    lines = ["Technical Skills", "Python, FastAPI"]
    pdf_bytes = _create_synthetic_text_pdf(lines)
    upload_res = client.post(
        "/api/v1/resumes/upload",
        files={"file": ("cv.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
        headers=headers,
    )
    resume_id = upload_res.json()["id"]

    job_res = client.post(
        "/api/v1/jobs",
        json={
            "title": "Python API Developer",
            "description": "Requirements: Python, FastAPI.\nPreferred: Docker.",
        },
        headers=headers,
    )
    job_id = job_res.json()["id"]

    res = client.post(
        f"/api/v1/matching/resumes/{resume_id}/jobs/{job_id}?use_semantic=true",
        headers=headers,
    )
    assert res.status_code == 200
    data = res.json()

    scores = data["scores"]
    assert scores["similarity_mode"] == "semantic"
    assert scores["is_fallback"] is False
    assert scores["applied_weights"] == {
        "required_skills": 0.50,
        "semantic_similarity": 0.30,
        "preferred_skills": 0.20,
    }

    # req_cov = 1.0, sem_sim = 0.80, pref_cov = 0.0
    # expected = round((0.50 * 1.0 + 0.30 * 0.80 + 0.20 * 0.0) * 100.0, 2) = 74.0
    assert scores["overall_score"] == 74.0

    # Summary cites semantic neural alignment
    assert "Semantic textual alignment is 80%" in data["explanation_summary"]


def test_complete_match_all_skills_present(client: TestClient):
    """When all required skills are present, summary notes full coverage and no high-priority gaps."""
    token = _get_auth_token(client, "full_match@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    lines = ["Technical Skills", "Python, SQL, Git"]
    pdf_bytes = _create_synthetic_text_pdf(lines)
    upload_res = client.post(
        "/api/v1/resumes/upload",
        files={"file": ("full_cv.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
        headers=headers,
    )
    resume_id = upload_res.json()["id"]

    job_res = client.post(
        "/api/v1/jobs",
        json={
            "title": "Junior Python Dev",
            "description": "Requirements: Python, SQL.",
        },
        headers=headers,
    )
    job_id = job_res.json()["id"]

    res = client.post(f"/api/v1/matching/resumes/{resume_id}/jobs/{job_id}", headers=headers)
    assert res.status_code == 200
    data = res.json()

    assert "All specified core required skills are present on your resume" in data["explanation_summary"]
    # No high-priority recommendations
    high_recs = [r for r in data["recommendations"] if r["priority"] == "high"]
    assert len(high_recs) == 0

