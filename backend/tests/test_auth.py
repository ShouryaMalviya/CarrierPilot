"""Integration and unit tests for authentication, password hashing, and session management."""

from datetime import timedelta
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.deps import get_db
from app.core.security import create_access_token, hash_password, verify_password
from app.db.base import Base
from app.main import app
from app.models import Profile, User


@event.listens_for(Engine, "connect")
def _set_sqlite_pragma(dbapi_connection, connection_record):
    """Enforce foreign key constraints in SQLite test engine."""
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


@pytest.fixture
def test_db():
    """Create an isolated in-memory test database with StaticPool and check_same_thread=False."""
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


def test_password_hashing():
    """Verify bcrypt salt, hashing, and verification."""
    password = "SuperSecretPassword123!"
    hashed = hash_password(password)

    assert hashed.startswith("$2b$")
    assert hashed != password
    assert verify_password(password, hashed) is True
    assert verify_password("WrongPassword123!", hashed) is False


def test_register_success(client, test_db):
    """Verify clean user registration and profile creation."""
    payload = {"email": "student@careerpilot.ai", "password": "SecurePassword123!"}
    response = client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "student@careerpilot.ai"
    assert data["is_active"] is True
    assert data["is_verified"] is False
    assert "id" in data

    # Verify user exists in database and password is encrypted
    user = test_db.query(User).filter_by(email="student@careerpilot.ai").first()
    assert user is not None
    assert user.hashed_password.startswith("$2b$")
    assert "SecurePassword123!" not in user.hashed_password

    # Verify default profile was auto-created
    profile = test_db.query(Profile).filter_by(user_id=user.id).first()
    assert profile is not None
    assert profile.target_role == "Junior Python Developer"


def test_register_duplicate_email(client):
    """Verify that registering the same email twice returns 400 Bad Request."""
    payload = {"email": "duplicate@careerpilot.ai", "password": "SecurePassword123!"}
    res1 = client.post("/api/v1/auth/register", json=payload)
    assert res1.status_code == 201

    res2 = client.post("/api/v1/auth/register", json=payload)
    assert res2.status_code == 400
    data = res2.json()
    assert "error" in data
    assert data["error"]["code"] == "EMAIL_ALREADY_REGISTERED"


def test_register_weak_password(client):
    """Verify password length constraints (< 8 characters rejected with 422)."""
    payload = {"email": "short@careerpilot.ai", "password": "short"}
    response = client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 422
    data = response.json()
    assert data["error"]["code"] == "VALIDATION_ERROR"


def test_login_success(client):
    """Verify valid login returns signed JWT access token."""
    client.post(
        "/api/v1/auth/register",
        json={"email": "login@careerpilot.ai", "password": "CorrectPassword123!"},
    )

    login_payload = {"email": "login@careerpilot.ai", "password": "CorrectPassword123!"}
    response = client.post("/api/v1/auth/login", json=login_payload)
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["expires_in"] > 0


def test_login_invalid_password(client):
    """Verify invalid password returns 401 with generic error message."""
    client.post(
        "/api/v1/auth/register",
        json={"email": "authfail@careerpilot.ai", "password": "CorrectPassword123!"},
    )

    response = client.post(
        "/api/v1/auth/login",
        json={"email": "authfail@careerpilot.ai", "password": "IncorrectPassword!"},
    )
    assert response.status_code == 401
    data = response.json()
    assert data["error"]["code"] == "INVALID_CREDENTIALS"


def test_login_nonexistent_email(client):
    """Verify unknown email returns 401 with generic error message to prevent enumeration."""
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "nonexistent@careerpilot.ai", "password": "SomePassword123!"},
    )
    assert response.status_code == 401
    data = response.json()
    assert data["error"]["code"] == "INVALID_CREDENTIALS"


def test_get_me_success(client):
    """Verify protected /me endpoint returns current authenticated user."""
    client.post(
        "/api/v1/auth/register",
        json={"email": "me@careerpilot.ai", "password": "ValidPassword123!"},
    )
    login_res = client.post(
        "/api/v1/auth/login",
        json={"email": "me@careerpilot.ai", "password": "ValidPassword123!"},
    )
    token = login_res.json()["access_token"]

    response = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "me@careerpilot.ai"


def test_get_me_missing_token(client):
    """Verify unauthenticated call to /me returns 401."""
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 401
    data = response.json()
    assert data["error"]["code"] == "NOT_AUTHENTICATED"


def test_get_me_invalid_token(client):
    """Verify invalid/tampered token returns 401."""
    response = client.get("/api/v1/auth/me", headers={"Authorization": "Bearer not-a-valid-token"})
    assert response.status_code == 401
    data = response.json()
    assert data["error"]["code"] == "INVALID_TOKEN"


def test_get_me_expired_token(client, test_db):
    """Verify expired token returns 401 with TOKEN_EXPIRED code."""
    # Create user directly
    user = User(email="expired@careerpilot.ai", hashed_password="pw")
    test_db.add(user)
    test_db.commit()

    # Create expired token (expired 1 hour ago)
    expired_token = create_access_token(
        data={"sub": str(user.id), "email": user.email},
        expires_delta=timedelta(hours=-1),
    )

    response = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {expired_token}"})
    assert response.status_code == 401
    data = response.json()
    assert data["error"]["code"] == "TOKEN_EXPIRED"


def test_logout(client):
    """Verify logout returns 200 acknowledgment."""
    response = client.post("/api/v1/auth/logout")
    assert response.status_code == 200
    assert "Logged out successfully" in response.json()["message"]
