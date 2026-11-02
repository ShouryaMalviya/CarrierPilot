"""Fixture-based tests for deterministic PDF/DOCX text extraction."""

import io
import zipfile
import docx
import pypdf
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.deps import get_db
from app.db.base import Base
from app.main import app
from app.services.text_extraction import (
    extract_text_from_docx,
    extract_text_from_pdf,
    normalize_extracted_text,
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


def _create_synthetic_blank_pdf() -> bytes:
    """Build a valid PDF with one blank page (simulating scanned/image document)."""
    writer = pypdf.PdfWriter()
    writer.add_blank_page(width=612, height=792)
    buf = io.BytesIO()
    writer.write(buf)
    return buf.getvalue()


def _create_synthetic_encrypted_pdf() -> bytes:
    """Build a password-encrypted PDF."""
    writer = pypdf.PdfWriter()
    writer.add_blank_page(width=612, height=792)
    writer.encrypt("top-secret-password")
    buf = io.BytesIO()
    writer.write(buf)
    return buf.getvalue()


def _create_synthetic_docx(paragraphs: list[str], table_rows: list[list[str]] = None) -> bytes:
    """Build a valid DOCX document using python-docx."""
    doc = docx.Document()
    for p in paragraphs:
        doc.add_paragraph(p)
    if table_rows:
        table = doc.add_table(rows=len(table_rows), cols=len(table_rows[0]))
        for r_idx, row in enumerate(table_rows):
            for c_idx, cell_value in enumerate(row):
                table.cell(r_idx, c_idx).text = cell_value
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


def test_normalize_extracted_text():
    """Verify text normalization preserves section breaks and trims noise."""
    raw = "Section 1: Skills   \r\n\r\n\r\nPython, FastAPI\xa0\xa0\n\n\nExperience:\nEngineer   "
    normalized = normalize_extracted_text(raw)
    assert "\r" not in normalized
    assert "\xa0" not in normalized
    assert "Section 1: Skills\n\nPython, FastAPI\n\nExperience:\nEngineer" == normalized


def test_extract_text_from_pdf_success():
    """Verify deterministic extraction of text lines from a valid synthetic PDF."""
    lines = ["Candidate: Jane Doe", "Skills: Python, SQLAlchemy, Docker", "Education: B.Tech Computer Science"]
    pdf_bytes = _create_synthetic_text_pdf(lines)

    result = extract_text_from_pdf(pdf_bytes)
    assert result.status == "completed"
    assert result.page_count == 1
    assert "Jane Doe" in result.text
    assert "Python, SQLAlchemy" in result.text
    assert len(result.warnings) == 0


def test_extract_text_from_pdf_scanned_image_warning():
    """Verify that image-only or blank PDFs trigger OCR unsupported warning."""
    blank_bytes = _create_synthetic_blank_pdf()
    result = extract_text_from_pdf(blank_bytes)

    assert result.status == "warning"
    assert result.page_count == 1
    assert any("OCR is not currently supported" in w for w in result.warnings)


def test_extract_text_from_pdf_encrypted():
    """Verify that password-encrypted PDFs return a safe warning without crashing."""
    encrypted_bytes = _create_synthetic_encrypted_pdf()
    result = extract_text_from_pdf(encrypted_bytes)

    assert result.status == "failed"
    assert any("password-protected" in w.lower() or "encrypted" in w.lower() for w in result.warnings)


def test_extract_text_from_pdf_corrupt():
    """Verify that corrupt PDF bytes fail safely without crashing."""
    corrupt_bytes = b"%PDF-1.4\ncorrupt content that breaks xref and headers"
    result = extract_text_from_pdf(corrupt_bytes)

    assert result.status == "failed"
    assert len(result.warnings) > 0


def test_extract_text_from_docx_success():
    """Verify extraction of paragraphs and table data from a synthetic DOCX."""
    paras = ["Candidate: Alex Smith", "Experience: 3 years building web apps", "Core Competencies:"]
    tables = [["Python", "FastAPI"], ["PostgreSQL", "Git"]]
    docx_bytes = _create_synthetic_docx(paras, tables)

    result = extract_text_from_docx(docx_bytes)
    assert result.status == "completed"
    assert "Alex Smith" in result.text
    assert "Python | FastAPI" in result.text
    assert len(result.warnings) == 0


def test_extract_text_from_docx_empty():
    """Verify that empty DOCX files return an empty-text warning."""
    empty_docx = _create_synthetic_docx([])
    result = extract_text_from_docx(empty_docx)

    assert result.status == "warning"
    assert any("no extractable text" in w.lower() for w in result.warnings)


def test_api_upload_and_auto_extract_pdf(client):
    """Verify uploading a text PDF via API automatically populates parsed_content."""
    token = _get_auth_token(client, "auto_extract_user@example.com")
    lines = ["Name: Test Candidate", "Skills: Python, Scikit-Learn", "Projects: Placement Coach"]
    pdf_bytes = _create_synthetic_text_pdf(lines)

    files = {"file": ("resume_candidate.pdf", io.BytesIO(pdf_bytes), "application/pdf")}
    response = client.post(
        "/api/v1/resumes/upload",
        files=files,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["parse_status"] == "completed"
    assert "pypdf" in data["parser_version"]
    assert "Test Candidate" in data["parsed_content"]["text"]
    assert "Scikit-Learn" in data["parsed_content"]["text"]


def test_api_upload_scanned_pdf_returns_warning(client):
    """Verify uploading a scanned PDF via API stores warning in parsed_content."""
    token = _get_auth_token(client, "scanned_user@example.com")
    blank_bytes = _create_synthetic_blank_pdf()

    files = {"file": ("scanned_resume.pdf", io.BytesIO(blank_bytes), "application/pdf")}
    response = client.post(
        "/api/v1/resumes/upload",
        files=files,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["parse_status"] == "warning"
    assert any("OCR is not currently supported" in w for w in data["parsed_content"]["warnings"])


def test_api_retrigger_extraction(client):
    """Verify re-running extraction endpoint on an existing resume record."""
    token = _get_auth_token(client, "retrigger_user@example.com")
    lines = ["Retrigger Test Content", "Skills: Alembic, Pydantic"]
    pdf_bytes = _create_synthetic_text_pdf(lines)

    files = {"file": ("retrigger.pdf", io.BytesIO(pdf_bytes), "application/pdf")}
    upload_res = client.post(
        "/api/v1/resumes/upload",
        files=files,
        headers={"Authorization": f"Bearer {token}"},
    )
    resume_id = upload_res.json()["id"]

    # Trigger re-extraction
    re_res = client.post(
        f"/api/v1/resumes/{resume_id}/extract",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert re_res.status_code == 200
    data = re_res.json()
    assert data["parse_status"] == "completed"
    assert "Alembic, Pydantic" in data["parsed_content"]["text"]
