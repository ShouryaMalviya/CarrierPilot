# CareerPilot AI — Backend Service

## Overview
FastAPI modular monolith backend providing authenticated REST APIs, deterministic NLP parsing, explainable hybrid job matching, adaptive diagnostic practice, and rubric-based mock interview coaching.

---

## 1. Prerequisites & Runtimes
- **Python**: 3.13.4 (or 3.11+)
- **pip**: 25+
- **Virtual Environment**: `.venv` in repository root or `backend/.venv`

---

## 2. Setup & Virtual Environment
From the repository root:
```powershell
# 1. Create a Python 3.13 virtual environment
python -m venv .venv

# 2. Activate the virtual environment
# Windows (PowerShell):
.\.venv\Scripts\Activate.ps1
# Windows (Command Prompt):
# .\.venv\Scripts\activate.bat
# Linux / macOS:
# source .venv/bin/activate

# 3. Upgrade pip and install pinned backend dependencies
pip install -r backend/requirements.txt
```

---

## 3. Database Configuration
CareerPilot AI is architected for PostgreSQL in production and defaults to SQLite for local development and testing:

- **Local Development / Testing (Default)**:
  `DATABASE_URL=sqlite:///./careerpilot.db` (zero configuration needed).
- **PostgreSQL (Optional / Production)**:
  1. Ensure a PostgreSQL 15+ server is running.
  2. Set connection string in `.env`:
     ```env
     DATABASE_URL=postgresql://<user>:<password>@localhost:5432/careerpilot
     ```
  3. When using PostgreSQL, ensure `psycopg2-binary` or `asyncpg` driver is installed if utilizing postgres-specific dialects.

---

## 4. NLP & Machine Learning Models

### Default Deterministic Lexical Baseline (Zero Downloads)
By default, `ENABLE_SEMANTIC_EMBEDDINGS=false`. The system relies exclusively on `scikit-learn` TF-IDF vectorization and exact/canonical skill matching. This requires:
- 0 MB external model downloads.
- 0 API keys.
- Completely offline and deterministic execution.

### Optional Semantic Model (Sentence Transformers)
When `ENABLE_SEMANTIC_EMBEDDINGS=true`:
- Model: `all-MiniLM-L6-v2` (~80 MB)
- Model cache directory: `~/.cache/huggingface/hub`
- Fallback behavior: If download fails or dependencies are missing, the matching service automatically degrades to the lexical TF-IDF ranker with an explanatory warning flag in the API response.

---

## 5. Configuration & Environment Settings
Configuration is managed via Pydantic Settings in `app/core/config.py`. It reads from environment variables or a local `.env` file (copied from `.env.example`).

- Missing non-critical keys (such as `AI_API_KEY`) default to local deterministic fallbacks (`AI_PROVIDER=local`).
- Critical keys (such as `SECRET_KEY` $\ge 16$ characters) are validated on startup with descriptive error messages.

---

## 6. Running Tests & Development Server
```powershell
# Run backend pytest suite
.\.venv\Scripts\pytest backend\tests

# Run with verbose output and coverage
.\.venv\Scripts\pytest backend\tests -v

# Start FastAPI development server (once app entry point is ready in Part 05)
.\.venv\Scripts\uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```
