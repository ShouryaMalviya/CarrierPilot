"""Integration tests for secure resume upload, validation, and storage lifecycle."""

import io
import os
import zipfile
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.deps import get_db
from app.db.base import Base
from app.main import app
from app.models import Resume, User


@event.listens_for(Engine, "connect")
def _set_sqlite_pragma(dbapi_connection, connection_record):
    """Enforce foreign key constraints in SQLite test engine."""
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


@pytest.fixture
def test_db(tmp_path):
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


def _create_synthetic_pdf_bytes(text: str = "Candidate Experience") -> bytes:
    """Generate a minimal valid synthetic PDF header and body."""
    return b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n" + text.encode("utf-8")


def _create_synthetic_docx_bytes() -> bytes:
    """Generate a minimal valid synthetic DOCX zip archive."""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", '<?xml version="1.0" encoding="UTF-8"?><Types></Types>')
        zf.writestr("word/document.xml", '<?xml version="1.0" encoding="UTF-8"?><w:document></w:document>')
    return buffer.getvalue()


def test_upload_valid_pdf_success(client):
    """Verify valid synthetic PDF uploads, stores with UUID key, and persists metadata."""
    token = _get_auth_token(client, "pdf_user@example.com")
    pdf_bytes = _create_synthetic_pdf_bytes()

    files = {"file": ("my_resume.pdf", io.BytesIO(pdf_bytes), "application/pdf")}
    response = client.post(
        "/api/v1/resumes/upload",
        files=files,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["original_filename"] == "my_resume.pdf"
    assert data["mime_type"] == "application/pdf"
    assert data["parse_status"] == "pending"
    assert len(data["file_key"]) == 32  # UUID hex key
    assert data["file_size_bytes"] == len(pdf_bytes)


def test_upload_valid_docx_success(client):
    """Verify valid synthetic DOCX uploads and stores cleanly."""
    token = _get_auth_token(client, "docx_user@example.com")
    docx_bytes = _create_synthetic_docx_bytes()

    files = {
        "file": (
            "resume.docx",
            io.BytesIO(docx_bytes),
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )
    }
    response = client.post(
        "/api/v1/resumes/upload",
        files=files,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["original_filename"] == "resume.docx"
    assert "wordprocessingml" in data["mime_type"]


def test_upload_zero_byte_file_rejected(client):
    """Verify empty uploads are rejected with 400 Bad Request."""
    token = _get_auth_token(client, "empty_user@example.com")
    files = {"file": ("empty.pdf", io.BytesIO(b""), "application/pdf")}

    response = client.post(
        "/api/v1/resumes/upload",
        files=files,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "EMPTY_FILE"


def test_upload_oversized_file_rejected(client):
    """Verify uploads exceeding max size limit (5MB) are rejected with 413."""
    token = _get_auth_token(client, "oversized_user@example.com")
    # 5.5 MB payload starting with valid PDF magic bytes
    large_payload = b"%PDF-1.4\n" + b"X" * (5500 * 1024)
    files = {"file": ("huge.pdf", io.BytesIO(large_payload), "application/pdf")}

    response = client.post(
        "/api/v1/resumes/upload",
        files=files,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 413
    assert response.json()["error"]["code"] == "FILE_TOO_LARGE"


def test_upload_unsupported_extension_rejected(client):
    """Verify unsupported file extensions (.exe, .txt) are rejected with 400."""
    token = _get_auth_token(client, "unsupported_user@example.com")
    files = {"file": ("script.py", io.BytesIO(b"print('hello')"), "text/plain")}

    response = client.post(
        "/api/v1/resumes/upload",
        files=files,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "UNSUPPORTED_FILE_TYPE"


def test_upload_fake_pdf_signature_rejected(client):
    """Verify files with .pdf extension but invalid magic bytes are rejected."""
    token = _get_auth_token(client, "fakepdf_user@example.com")
    fake_content = b"This is just a plain text file pretending to be a PDF"
    files = {"file": ("fake.pdf", io.BytesIO(fake_content), "application/pdf")}

    response = client.post(
        "/api/v1/resumes/upload",
        files=files,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "INVALID_PDF_SIGNATURE"


def test_upload_corrupt_docx_rejected(client):
    """Verify files with .docx extension but invalid zip structure are rejected."""
    token = _get_auth_token(client, "fakedocx_user@example.com")
    fake_content = b"PK\x03\x04not-a-valid-zip-content"
    files = {"file": ("fake.docx", io.BytesIO(fake_content), "application/vnd.openxmlformats-officedocument")}

    response = client.post(
        "/api/v1/resumes/upload",
        files=files,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 400


def test_resume_ownership_isolation(client):
    """Verify User B cannot access or delete User A's resume by guessing ID."""
    token_a = _get_auth_token(client, "user_a_resumes@example.com")
    token_b = _get_auth_token(client, "user_b_resumes@example.com")

    # User A uploads resume
    pdf_bytes = _create_synthetic_pdf_bytes("User A Confidential Resume")
    files = {"file": ("user_a_resume.pdf", io.BytesIO(pdf_bytes), "application/pdf")}
    upload_res = client.post(
        "/api/v1/resumes/upload",
        files=files,
        headers={"Authorization": f"Bearer {token_a}"},
    )
    resume_a_id = upload_res.json()["id"]

    # User B attempts to access User A's resume -> 404 Not Found
    res_b_get = client.get(
        f"/api/v1/resumes/{resume_a_id}",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert res_b_get.status_code == 404
    assert res_b_get.json()["error"]["code"] == "RESUME_NOT_FOUND"

    # User B attempts to delete User A's resume -> 404 Not Found
    res_b_del = client.delete(
        f"/api/v1/resumes/{resume_a_id}",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert res_b_del.status_code == 404
    assert res_b_del.json()["error"]["code"] == "RESUME_NOT_FOUND"

    # User A CAN access their own resume
    res_a_get = client.get(
        f"/api/v1/resumes/{resume_a_id}",
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert res_a_get.status_code == 200
    assert res_a_get.json()["id"] == resume_a_id


def test_delete_resume_removes_physical_file(client, test_db):
    """Verify deleting a resume removes the DB record and deletes file from storage."""
    token = _get_auth_token(client, "clean_user@example.com")
    pdf_bytes = _create_synthetic_pdf_bytes()

    files = {"file": ("delete_me.pdf", io.BytesIO(pdf_bytes), "application/pdf")}
    upload_res = client.post(
        "/api/v1/resumes/upload",
        files=files,
        headers={"Authorization": f"Bearer {token}"},
    )
    resume_id = upload_res.json()["id"]

    # Verify physical file exists on disk
    resume_record = test_db.query(Resume).filter_by(id=resume_id).first()
    assert resume_record is not None
    file_path = resume_record.file_path
    assert os.path.exists(file_path)

    # Delete resume
    del_res = client.delete(f"/api/v1/resumes/{resume_id}", headers={"Authorization": f"Bearer {token}"})
    assert del_res.status_code == 200
    assert "deleted successfully" in del_res.json()["message"]

    # Verify physical file was removed from storage
    assert not os.path.exists(file_path)

    # Verify database record was deleted
    assert test_db.query(Resume).filter_by(id=resume_id).first() is None

