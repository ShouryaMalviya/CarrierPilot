"""Tests for lexical matching baseline: TF-IDF cosine similarity, skill gap analysis, and batch ranking."""

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
from app.models import Job, JobSkill, Resume, ResumeSkill, Skill
from app.schemas.matching import DEFAULT_MATCHING_DISCLAIMER
from app.services.job_parser import seed_synthetic_jobs
from app.services.matching_service import (
    compute_skill_gap,
    compute_tfidf_similarity,
    tokenize_text,
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
# Unit Tests: Tokenization and Similarity
# ==============================================================================


def test_tokenize_text():
    """Verify tokenizer lowercases, removes stop words, and preserves alphanumeric technical tokens."""
    text = "We are seeking a Python & C++ backend engineer with FastAPI knowledge."
    tokens = tokenize_text(text)
    assert "python" in tokens
    assert "fastapi" in tokens
    assert "are" not in tokens
    assert "with" not in tokens


def test_compute_tfidf_similarity_identical():
    """Identical texts should yield cosine similarity close to 1.0."""
    text = "Software Engineer experienced in Python, SQL databases, and Docker containerization."
    sim = compute_tfidf_similarity(text, text)
    assert sim >= 0.99


def test_compute_tfidf_similarity_empty():
    """Empty or whitespace strings should yield 0.0 similarity."""
    assert compute_tfidf_similarity("", "Python Developer") == 0.0
    assert compute_tfidf_similarity("   ", "") == 0.0
    assert compute_tfidf_similarity("Python", "   ") == 0.0


def test_compute_tfidf_similarity_disjoint():
    """Completely disjoint vocabularies should produce 0.0 similarity."""
    text_a = "Biology botany plants photosynthesis chlorophyll cellular"
    text_b = "Quantum mechanics physics bosons fermions relativity"
    sim = compute_tfidf_similarity(text_a, text_b)
    assert sim == 0.0


def test_compute_skill_gap_complete_coverage():
    """Resume possessing all required and preferred skills yields 1.0 coverage and no missing skills."""
    resume_skills = {"Python", "SQL", "Docker", "Git"}
    required_skills = {"Python", "SQL"}
    preferred_skills = {"Docker"}

    gap, req_cov, pref_cov = compute_skill_gap(resume_skills, required_skills, preferred_skills)

    assert req_cov == 1.0
    assert pref_cov == 1.0
    assert gap.matched_required == ["Python", "SQL"]
    assert gap.missing_required == []
    assert gap.matched_preferred == ["Docker"]
    assert gap.missing_preferred == []
    assert gap.additional_skills == ["Git"]


def test_compute_skill_gap_partial_and_missing():
    """Missing required and preferred skills are cleanly categorized with fractional coverage."""
    resume_skills = {"Python"}
    required_skills = {"Python", "SQL", "FastAPI"}
    preferred_skills = {"Docker", "PostgreSQL"}

    gap, req_cov, pref_cov = compute_skill_gap(resume_skills, required_skills, preferred_skills)

    assert req_cov == round(1 / 3, 4)
    assert pref_cov == 0.0
    assert gap.matched_required == ["Python"]
    assert set(gap.missing_required) == {"FastAPI", "SQL"}
    assert gap.matched_preferred == []
    assert set(gap.missing_preferred) == {"Docker", "PostgreSQL"}


def test_compute_skill_gap_empty_requirements():
    """When a job posting has no explicit requirements, coverage defaults safely to 1.0."""
    resume_skills = {"Python"}
    gap, req_cov, pref_cov = compute_skill_gap(resume_skills, set(), set())
    assert req_cov == 1.0
    assert pref_cov == 1.0
    assert gap.missing_required == []
    assert gap.missing_preferred == []


# ==============================================================================
# API Integration Tests: Resume-to-Job Matching & Batch Ranking
# ==============================================================================


def test_match_resume_to_job_api_success(client: TestClient):
    """Candidate matches their uploaded resume against a target job with explainable breakdown."""
    token = _get_auth_token(client, "candidate_match@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Upload a resume
    resume_lines = [
        "Professional Summary",
        "Junior Python developer with FastAPI and SQL experience.",
        "Technical Skills",
        "Python, FastAPI, SQL, Git",
    ]
    pdf_bytes = _create_synthetic_text_pdf(resume_lines)
    upload_res = client.post(
        "/api/v1/resumes/upload",
        files={"file": ("match_cv.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
        headers=headers,
    )
    assert upload_res.status_code == 201
    resume_id = upload_res.json()["id"]

    # 2. Create a target job
    job_payload = {
        "title": "Junior Python Backend Engineer",
        "company": "FastTech Solutions",
        "description": (
            "We are hiring a Junior Python Backend Engineer.\n\n"
            "Requirements:\n"
            "Proficiency in Python and FastAPI.\n"
            "Knowledge of SQL databases.\n\n"
            "Preferred:\n"
            "Hands-on exposure to Docker is a plus."
        ),
    }
    job_res = client.post("/api/v1/jobs", json=job_payload, headers=headers)
    assert job_res.status_code == 201
    job_id = job_res.json()["id"]

    # 3. Request match evaluation
    match_res = client.post(f"/api/v1/matching/resumes/{resume_id}/jobs/{job_id}", headers=headers)
    assert match_res.status_code == 200
    data = match_res.json()

    assert data["resume_id"] == resume_id
    assert data["job_id"] == job_id
    assert data["job_title"] == "Junior Python Backend Engineer"

    # Score breakdown assertions
    scores = data["scores"]
    assert scores["required_coverage"] == 1.0  # Python, FastAPI, SQL all present
    assert scores["preferred_coverage"] == 0.0  # Docker missing
    assert scores["tfidf_similarity"] > 0.10
    assert scores["overall_score"] > 60.0  # 0.60 * 1.0 + 0.20 * 0.0 + 0.20 * sim

    # Skill gap assertions
    gap = data["skill_gap"]
    assert "Python" in gap["matched_required"]
    assert "FastAPI" in gap["matched_required"]
    assert "SQL" in gap["matched_required"]
    assert "Docker" in gap["missing_preferred"]
    assert "Git" in gap["additional_skills"]

    # Mandatory disclaimer assertion
    assert data["disclaimer"] == DEFAULT_MATCHING_DISCLAIMER


def test_batch_match_resumes_ranking(client: TestClient):
    """Batch match ranks accessible jobs by overall match score in descending order."""
    token = _get_auth_token(client, "batch_candidate@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Seed public synthetic benchmark jobs (Junior Python Dev & Entry-Level Data Analyst)
    client.post("/api/v1/jobs/seed-demo", headers=headers)

    # 2. Upload Python-focused resume
    resume_lines = [
        "Technical Skills",
        "Python, FastAPI, SQL, Git, Docker",
    ]
    pdf_bytes = _create_synthetic_text_pdf(resume_lines)
    upload_res = client.post(
        "/api/v1/resumes/upload",
        files={"file": ("python_cv.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
        headers=headers,
    )
    resume_id = upload_res.json()["id"]

    # 3. Call batch match
    batch_res = client.post(f"/api/v1/matching/resumes/{resume_id}/batch", headers=headers)
    assert batch_res.status_code == 200
    data = batch_res.json()

    assert data["resume_id"] == resume_id
    assert data["total_jobs_evaluated"] >= 2
    matches = data["matches"]
    assert len(matches) >= 2

    # Verify descending ordering of scores
    scores = [m["overall_score"] for m in matches]
    assert scores == sorted(scores, reverse=True)

    # Top match should be Junior Python Developer fixture
    top_match = matches[0]
    assert "Python" in top_match["job_title"]
    assert top_match["required_coverage"] >= 0.75
    assert data["disclaimer"] == DEFAULT_MATCHING_DISCLAIMER


def test_match_ownership_isolation(client: TestClient):
    """User B cannot evaluate User A's private resume or private job."""
    token_a = _get_auth_token(client, "alice_match@example.com")
    token_b = _get_auth_token(client, "bob_match@example.com")

    # Alice uploads resume
    pdf_bytes = _create_synthetic_text_pdf(["Technical Skills", "Python, FastAPI"])
    res_a = client.post(
        "/api/v1/resumes/upload",
        files={"file": ("alice_cv.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
        headers={"Authorization": f"Bearer {token_a}"},
    )
    alice_resume_id = res_a.json()["id"]

    # Alice creates private job
    job_a = client.post(
        "/api/v1/jobs",
        json={"title": "Private Role", "description": "Requirements: Must know Python."},
        headers={"Authorization": f"Bearer {token_a}"},
    )
    alice_job_id = job_a.json()["id"]

    # Bob attempts to match Alice's resume against Alice's job -> 404
    match_b = client.post(
        f"/api/v1/matching/resumes/{alice_resume_id}/jobs/{alice_job_id}",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert match_b.status_code == 404
    assert match_b.json()["error"]["code"] == "RESUME_NOT_FOUND"

    # Bob uploads his own resume
    res_b = client.post(
        "/api/v1/resumes/upload",
        files={"file": ("bob_cv.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
        headers={"Authorization": f"Bearer {token_b}"},
    )
    bob_resume_id = res_b.json()["id"]

    # Bob attempts to match his resume against Alice's private job -> 404
    match_b_to_a = client.post(
        f"/api/v1/matching/resumes/{bob_resume_id}/jobs/{alice_job_id}",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert match_b_to_a.status_code == 404
    assert match_b_to_a.json()["error"]["code"] == "JOB_NOT_FOUND"


def test_match_unauthenticated(client: TestClient):
    """Endpoints require authentication, returning 401 Unauthorized."""
    res = client.post("/api/v1/matching/resumes/1/jobs/1")
    assert res.status_code == 401

    res_batch = client.post("/api/v1/matching/resumes/1/batch")
    assert res_batch.status_code == 401

