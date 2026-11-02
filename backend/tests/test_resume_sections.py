"""Integration and unit tests for resume section segmentation, skill extraction, and user corrections."""

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
from app.models import Resume, ResumeSkill, Skill, User
from app.services.section_parser import (
    extract_skills_with_evidence,
    segment_resume_sections,
)
from app.services.skill_taxonomy import normalize_skill_name


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


def test_segment_resume_sections():
    """Verify section segmentation correctly parses headers."""
    sample_text = (
        "Professional Summary\n"
        "Passionate junior developer eager to build software.\n"
        "Technical Skills\n"
        "Python, FastAPI, PostgreSQL, Git\n"
        "Work Experience\n"
        "Software Engineering Intern at TechCorp\n"
        "Projects\n"
        "Placement Intelligence Coach using ML and NLP\n"
        "Education\n"
        "Bachelor of Technology in Computer Science"
    )
    sections = segment_resume_sections(sample_text)

    assert "junior developer" in sections["summary"]
    assert "Python, FastAPI" in sections["skills"]
    assert "TechCorp" in sections["experience"]
    assert "Placement Intelligence" in sections["projects"]
    assert "Computer Science" in sections["education"]


def test_alias_normalization():
    """Verify alias normalization to canonical taxonomy strings."""
    assert normalize_skill_name("scikit learn") == "Scikit-Learn"
    assert normalize_skill_name("sklearn") == "Scikit-Learn"
    assert normalize_skill_name("fast api") == "FastAPI"
    assert normalize_skill_name("postgres") == "PostgreSQL"
    assert normalize_skill_name("python") == "Python"
    assert normalize_skill_name("PYTHON") == "Python"


def test_negation_handling():
    """Verify that negated skill mentions are skipped from automatic extraction."""
    text = (
        "Technical Skills\n"
        "Python, PostgreSQL\n"
        "Experience\n"
        "Built REST APIs in Python. Currently have no experience with Docker. Not familiar with Java."
    )
    extracted = extract_skills_with_evidence(text)
    extracted_names = [e["canonical_name"] for e in extracted]

    assert "Python" in extracted_names
    assert "PostgreSQL" in extracted_names
    assert "Docker" not in extracted_names
    assert "Java" not in extracted_names


def test_evidence_snippet_and_confidence():
    """Verify evidence sentence linking and confidence calibration by section."""
    text = (
        "Technical Skills\n"
        "Python, FastAPI\n"
        "Projects\n"
        "Trained models using Scikit-Learn on placement datasets"
    )
    sections = segment_resume_sections(text)
    extracted = extract_skills_with_evidence(text, sections)

    extracted_dict = {e["canonical_name"]: e for e in extracted}
    assert "Python" in extracted_dict
    assert extracted_dict["Python"]["confidence_score"] == 1.00
    assert "Python, FastAPI" in extracted_dict["Python"]["evidence_snippet"]

    assert "Scikit-Learn" in extracted_dict
    assert extracted_dict["Scikit-Learn"]["confidence_score"] == 0.90
    assert "Scikit-Learn" in extracted_dict["Scikit-Learn"]["evidence_snippet"]


def test_end_to_end_upload_and_skill_correction_workflow(client):
    """Full workflow: upload -> auto extract -> get sections -> add skill -> confirm skill -> delete skill."""
    token = _get_auth_token(client, "correction_user@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    lines = [
        "Technical Skills",
        "Python, FastAPI, SQL",
        "Projects",
        "Engineered backend pipelines with Pandas",
    ]
    pdf_bytes = _create_synthetic_text_pdf(lines)
    files = {"file": ("my_cv.pdf", io.BytesIO(pdf_bytes), "application/pdf")}

    # 1. Upload resume
    upload_res = client.post("/api/v1/resumes/upload", files=files, headers=headers)
    assert upload_res.status_code == 201
    resume_id = upload_res.json()["id"]

    # 2. Get sections and extracted skills
    sec_res = client.get(f"/api/v1/resumes/{resume_id}/sections", headers=headers)
    assert sec_res.status_code == 200
    sec_data = sec_res.json()
    extracted_skills = {s["canonical_name"]: s for s in sec_data["skills"]}
    assert "Python" in extracted_skills
    assert "FastAPI" in extracted_skills
    assert extracted_skills["Python"]["is_auto_extracted"] is True
    assert extracted_skills["Python"]["is_user_confirmed"] is False

    python_link_id = extracted_skills["Python"]["id"]

    # 3. User confirms an auto-extracted skill
    confirm_res = client.put(
        f"/api/v1/resumes/{resume_id}/skills/{python_link_id}",
        json={"is_user_confirmed": True},
        headers=headers,
    )
    assert confirm_res.status_code == 200
    assert confirm_res.json()["is_user_confirmed"] is True

    # 4. User adds a missing skill (e.g. Docker)
    add_res = client.post(
        f"/api/v1/resumes/{resume_id}/skills",
        json={"skill_name": "docker compose", "evidence_snippet": "Personal home lab server"},
        headers=headers,
    )
    assert add_res.status_code == 201
    add_data = add_res.json()
    assert add_data["canonical_name"] == "Docker"
    assert add_data["is_user_confirmed"] is True
    assert add_data["is_auto_extracted"] is False
    assert add_data["evidence_snippet"] == "Personal home lab server"
    docker_link_id = add_data["id"]

    # 5. User removes an incorrect skill / false positive (FastAPI)
    fastapi_link_id = extracted_skills["FastAPI"]["id"]
    del_res = client.delete(f"/api/v1/resumes/{resume_id}/skills/{fastapi_link_id}", headers=headers)
    assert del_res.status_code == 200

    # 6. Verify skill list reflects updates
    skills_list_res = client.get(f"/api/v1/resumes/{resume_id}/skills", headers=headers)
    assert skills_list_res.status_code == 200
    current_skills = {s["canonical_name"] for s in skills_list_res.json()}
    assert "Python" in current_skills
    assert "Docker" in current_skills
    assert "FastAPI" not in current_skills  # Removed

    # 7. User edits sections
    update_sec_res = client.put(
        f"/api/v1/resumes/{resume_id}/sections",
        json={"sections": {"skills": "Python, Docker, SQL", "projects": "Custom updated projects"}},
        headers=headers,
    )
    assert update_sec_res.status_code == 200
    assert update_sec_res.json()["sections"]["projects"] == "Custom updated projects"


def test_skill_correction_ownership_isolation(client):
    """Verify User B cannot view or modify User A's resume skills."""
    token_a = _get_auth_token(client, "owner_a@example.com")
    token_b = _get_auth_token(client, "owner_b@example.com")

    lines = ["Technical Skills", "Python, SQL"]
    pdf_bytes = _create_synthetic_text_pdf(lines)
    upload_res = client.post(
        "/api/v1/resumes/upload",
        files={"file": ("resume_a.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
        headers={"Authorization": f"Bearer {token_a}"},
    )
    resume_a_id = upload_res.json()["id"]

    # User B attempts to add skill to User A's resume -> 404
    res_b = client.post(
        f"/api/v1/resumes/{resume_a_id}/skills",
        json={"skill_name": "Docker"},
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert res_b.status_code == 404
