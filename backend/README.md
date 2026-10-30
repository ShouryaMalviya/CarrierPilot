# CareerPilot AI — Backend Service

## Overview
FastAPI modular monolith backend providing authenticated REST APIs, deterministic NLP parsing, hybrid job matching, adaptive question recommendation, and rubric-based mock interview coaching.

## Directory Layout
- `app/api/`: Versioned API endpoints (auth, profiles, resumes, jobs, practice, interviews, progress).
- `app/core/`: Application settings, security utilities (password hashing, JWT), and custom error handling.
- `app/db/`: Database session management, SQLAlchemy 2.0 declarative models, and Alembic migrations.
- `app/schemas/`: Pydantic request and response schemas (contracts).
- `app/services/`: Core business logic, resume parsers, TF-IDF ranker, and rubric coach.
- `tests/`: Pytest test suite covering unit logic, integration endpoints, and auth security.

## Setup & Execution Commands
```bash
# Activate virtual environment
# Windows:
..\.venv\Scripts\activate

# Install dependencies (pinned in Part 04)
pip install -r requirements.txt

# Run pytest suite
pytest

# Launch development server
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

