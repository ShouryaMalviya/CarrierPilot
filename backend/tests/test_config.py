"""Tests for the application configuration and settings module."""

import pytest
from pydantic import ValidationError
from app.core.config import Settings


def test_default_settings():
    """Verify that default settings instantiate with expected defaults."""
    settings = Settings(
        SECRET_KEY="test-secret-key-that-is-at-least-32-characters-long",
    )
    assert settings.ENVIRONMENT == "development"
    assert settings.DEBUG is True
    assert settings.PORT == 8000
    assert settings.AI_PROVIDER == "local"
    assert settings.AI_API_KEY is None
    assert settings.ENABLE_SEMANTIC_EMBEDDINGS is False
    assert settings.MAX_UPLOAD_SIZE_MB == 5
    assert "http://localhost:5173" in settings.CORS_ORIGINS


def test_cors_origins_parsing():
    """Verify comma-separated CORS origins string is safely parsed into a list."""
    settings = Settings(
        SECRET_KEY="test-secret-key-that-is-at-least-32-characters-long",
        CORS_ORIGINS="http://localhost:3000, https://careerpilot.ai, http://127.0.0.1:3000",
    )
    assert settings.CORS_ORIGINS == [
        "http://localhost:3000",
        "https://careerpilot.ai",
        "http://127.0.0.1:3000",
    ]


def test_secret_key_minimum_length():
    """Verify that a SECRET_KEY shorter than 16 characters raises a ValidationError."""
    with pytest.raises(ValidationError) as exc_info:
        Settings(SECRET_KEY="too-short")
    assert "SECRET_KEY" in str(exc_info.value)


def test_invalid_environment_rejected():
    """Verify that unsupported environment names are rejected."""
    with pytest.raises(ValidationError) as exc_info:
        Settings(
            SECRET_KEY="test-secret-key-that-is-at-least-32-characters-long",
            ENVIRONMENT="invalid-env",
        )
    assert "ENVIRONMENT" in str(exc_info.value)


def test_optional_ai_provider_missing_key():
    """Verify that missing AI credentials does not prevent settings from loading."""
    settings = Settings(
        SECRET_KEY="test-secret-key-that-is-at-least-32-characters-long",
        AI_PROVIDER="local",
        AI_API_KEY=None,
    )
    assert settings.AI_PROVIDER == "local"
    assert settings.AI_API_KEY is None

