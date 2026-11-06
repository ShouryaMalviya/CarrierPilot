# CareerPilot AI — Production Deployment & Operational Runbook

**Target Platform Version**: 1.0.0  
**Stack**: FastAPI (Python 3.13) + React 18 / TypeScript / Vite + SQLAlchemy 2.0 / Alembic + Nginx Alpine  

---

## 1. System Architecture Overview

```
+-------------------------------------------------------------------------+
|                              Client Browser                             |
|              (React 18 / TypeScript / Vite SPA on Port 5173)             |
+-------------------------------------------------------------------------+
                                    |
                                    | HTTP / JSON (REST API)
                                    v
+-------------------------------------------------------------------------+
|                           Nginx Reverse Proxy                           |
|      - Reverse proxies /api/v1/ -> backend:8000                         |
|      - Serves compiled static bundle (gzip, immutable caching)          |
|      - Enforces browser security headers (nosniff, frame-options, CSP)  |
+-------------------------------------------------------------------------+
                                    |
                                    v
+-------------------------------------------------------------------------+
|                         FastAPI Application (ASGI)                      |
|      - Port: 8000                                                       |
|      - Security Middleware & Strict CORS Validation                     |
|      - Hybrid Job Ranker (TF-IDF + Taxonomy Normalization)              |
|      - Adaptive MCQ Practice & Mastery Decay Engine (gamma=0.85)        |
|      - 5-Dimension Rubric Coaching & Prompt Injection Sanitizer         |
+-------------------------------------------------------------------------+
                     /                                  \
                    v                                    v
+--------------------------------------+   +------------------------------+
|            Persistence Layer         |   |    Private Document Storage  |
|  - SQLite (Dev/Demo: careerpilot.db) |   |  - Isolated Uploads Dir      |
|  - PostgreSQL 16+ (Production target)|   |  - Non-guessable UUID keys   |
+--------------------------------------+   +------------------------------+
```

---

## 2. Environment Variables & Configuration Reference

Create a `.env` file in the project root or configure environment variables in your container manager:

| Variable | Type | Default | Description |
| :--- | :---: | :---: | :--- |
| `ENVIRONMENT` | string | `development` | Deployment environment (`development`, `staging`, `production`). In production, interactive OpenAPI docs can be restricted. |
| `DEBUG` | boolean | `False` | Enables verbose debug logging. Always `False` in production. |
| `SECRET_KEY` | string | *Required* | 32+ character cryptographically secure secret for JWT signature verification. |
| `ALGORITHM` | string | `HS256` | JWT signing algorithm. |
| `ACCESS_TOKEN_EXPIRE_MINUTES`| integer | `120` | Session lifetime before re-authentication is required. |
| `DATABASE_URL` | string | `sqlite:///./careerpilot.db` | SQLAlchemy connection string (`postgresql://user:pass@host:5432/careerpilot` in production). |
| `UPLOAD_DIR` | string | `./uploads` | Storage directory for candidate resumes, strictly outside web root. |
| `MAX_UPLOAD_SIZE_BYTES` | integer | `10485760` | Maximum file size limit (10MB). |
| `CORS_ORIGINS` | JSON list | `["http://localhost:5173"]`| Whitelist of trusted frontend domains. |
| `AI_PROVIDER` | string | `local` | Evaluation provider (`local` for deterministic offline rubric; `gemini` for optional LLM adapter). |
| `GEMINI_API_KEY` | string | `""` | Optional API key when `AI_PROVIDER=gemini`. System defaults to local rubric fallback when blank. |

---

## 3. Deployment Option A: Multi-Container Docker Deployment

The repository includes production-ready container configurations (`Dockerfile`, `frontend/Dockerfile`, `docker-compose.yml`).

### Step 1: Clone and Configure
```bash
git clone https://github.com/YourOrg/CareerPilot.git
cd CareerPilot
cp .env.example .env
# Edit .env and supply a unique SECRET_KEY
```

### Step 2: Launch via Docker Compose
```bash
docker-compose up --build -d
```

### Step 3: Verify Container Health
```bash
docker-compose ps
# Verify backend:8000 and frontend:5173 report healthy
curl -f http://localhost:8000/api/v1/health
```

### Step 4: Seed Demo Benchmark Data
```bash
docker-compose exec backend python scripts/seed_demo_environment.py
```

The application is now live at:
- **Frontend SPA**: `http://localhost:5173`
- **Backend API**: `http://localhost:8000/api/v1`
- **Interactive OpenAPI Documentation**: `http://localhost:8000/docs`

---

## 4. Deployment Option B: Bare-Metal / Local Development Setup

For local evaluation, viva examination, or development environments:

### Windows (PowerShell)
```powershell
# 1. Activate virtual environment
.\.venv\Scripts\Activate.ps1

# 2. Run automated startup script
.\scripts\start_local.ps1
```

### Linux / macOS (Bash)
```bash
# 1. Make startup script executable and run
chmod +x scripts/start_local.sh
./scripts/start_local.sh
```

---

## 5. Database Migrations & Zero-Downtime Schema Updates

Schema changes are tracked via reversible Alembic migrations located in `backend/alembic/versions/`.

### Apply Migrations to Head:
```bash
cd backend
alembic upgrade head
```

### Check Current Migration Revision:
```bash
alembic current
```

### Generate a New Migration:
```bash
alembic revision --autogenerate -m "Add descriptive migration name"
```

### Rollback Previous Migration:
```bash
alembic downgrade -1
```

---

## 6. Backup, Recovery & Data Portability Runbook

### SQLite Database Backup:
```bash
# Atomic online backup of SQLite database file
sqlite3 careerpilot.db ".backup 'backups/careerpilot_backup_$(date +%F).db'"
```

### Resume Storage Volume Backup:
```bash
tar -czvf "backups/resume_uploads_$(date +%F).tar.gz" uploads/
```

### Candidate GDPR Data Portability:
Candidates can trigger a complete export of their personal profile, uploaded resumes, diagnostic practice history, topic masteries, and mock interview transcripts directly through the UI (`/progress` -> "Export My Data") or programmatically:
```bash
curl -H "Authorization: Bearer <TOKEN>" http://localhost:8000/api/v1/progress/dashboard
```

---

## 7. Security Hardening Checklist

Prior to public production exposure:
- [x] **Secret Isolation**: `SECRET_KEY` loaded exclusively from environment variables, never committed to git.
- [x] **Directory Traversal Defense**: Resume uploads assigned UUID keys (`file_key`), private storage outside web root (`UPLOAD_DIR`).
- [x] **File Validation**: Strict magic-byte header validation for PDF (`%PDF-`) and DOCX (`PK\x03\x04`), 10MB size enforcement.
- [x] **Security Headers**: Standard Nginx and FastAPI middleware headers enabled (`X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy: strict-origin-when-cross-origin`).
- [x] **Prompt Injection Defense**: Multi-pattern regex sanitizer (`PROMPT_INJECTION_PATTERNS`) and immutable audit logging.
- [x] **Zero Biometric Inferences**: Architecture explicitly omits webcam, microphone, and psychometric inference pipelines.
- [x] **Ethical Disclaimers**: Statutory educational non-guarantee disclosures attached to every scoring endpoint.

