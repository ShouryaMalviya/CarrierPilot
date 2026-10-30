# CareerPilot AI

> **Personalized Placement Intelligence & Adaptive Interview Coach**  
> An explainable, evidence-backed preparation platform for fresh graduates and students.

---

## 1. Product Overview

CareerPilot AI bridges the gap between graduation and campus placement by unifying five core preparation workflows into an explainable, modular platform:

1. **Resume Ingestion & Evidence-Based Extraction**: Deterministic text parsing with user-editable fields and traceable text evidence snippets.
2. **Explainable Job Matching**: Transparent skill-gap analysis combining required skill coverage, semantic similarity, and preferred skill coverage with component-level score breakdowns.
3. **Tagged Diagnostic & Adaptive Practice**: Curated question bank tagged by topic and difficulty, paired with a transparent recent-weighted mastery heuristic and explainable recommendations.
4. **Structured Mock Interviews with Rubric Coaching**: Typed-first technical interviews evaluated against a five-dimension rubric citing specific answer evidence.
5. **Progress Tracking & Evaluation**: Auditable learner dashboards and an evaluation harness using frozen synthetic benchmark datasets.

### Strict Product Guardrails
- **No Placement Guarantees**: CareerPilot AI provides relevance scores and coaching guidance; it never claims to predict hiring or guarantee jobs.
- **Typed-First & Zero Biometric Inference**: Operates 100% via typed text; never infers personality, honesty, confidence, or emotional state from audio or video.
- **Deterministic Core**: All features work locally without requiring paid third-party AI credentials.

---

## 2. Directory Structure

```text
CareerPilot/
├── backend/               # FastAPI modular backend
│   ├── app/               # Application package (API, core, db, schemas, services)
│   ├── tests/             # Pytest suite (unit, integration, contracts)
│   └── README.md          # Backend setup and run instructions
├── frontend/              # React + TypeScript + Vite web client
│   ├── src/               # React components, pages, services, types
│   └── README.md          # Frontend setup and run instructions
├── docs/                  # Architecture and implementation specifications
│   ├── architecture.md    # System design, data flows, and security policies
│   └── implementation_plan.md # 40-part incremental execution roadmap
├── evaluation/            # ML evaluation scripts, frozen datasets, and metrics
│   └── README.md          # Evaluation instructions and metric definitions
├── scripts/               # Operational, seeding, and verification helper scripts
│   └── README.md          # Script documentation
├── .env.example           # Safe placeholder environment template (no secrets)
├── .gitignore             # Git ignore rules for virtualenvs, node_modules, and secrets
└── README.md              # Project overview and root instructions
```

---

## 3. Quick Start & Setup

### Prerequisites
- **Python**: 3.13+ with `pip`
- **Node.js**: 20+ with `npm`
- **Git**

### Backend Setup
```bash
# Navigate to backend directory
cd backend

# Create and activate a Python virtual environment
python -m venv .venv
# On Windows:
.venv\Scripts\activate
# On Linux/macOS:
# source .venv/bin/activate

# Install dependencies (configured in Part 04)
pip install -r requirements.txt

# Copy environment configuration from template
cp ../.env.example .env

# Run tests
pytest

# Start development server
uvicorn app.main:app --reload --port 8000
```

### Frontend Setup
```bash
# Navigate to frontend directory
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

---

## 4. Documentation Links

- [System Architecture Specification](file:///c:/Users/SHOURYA/CarrierPilot/docs/architecture.md)
- [40-Part Implementation Plan](file:///c:/Users/SHOURYA/CarrierPilot/docs/implementation_plan.md)
