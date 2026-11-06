# CareerPilot AI — 40-Part Incremental Implementation Plan

## 1. Overview & Execution Protocol
This implementation plan defines the sequenced, phase-gated execution of **CareerPilot AI**. Each part represents a single, scoped increment executed under the **Global Master Prompt** and validated by the **Verify / Repair Loop**.

### Core Execution Rules
1. **One Part at a Time**: No premature implementation of downstream parts.
2. **Repository Truth**: Every test or build status must be backed by real command executions and terminal outputs.
3. **Strict Bounds on Repairs**: Up to 3 repair cycles per failure before escalating blockers.
4. **Deterministic Fallbacks**: Core functionality must remain testable and demonstrable without paid third-party API keys or active internet access.
5. **Privacy by Default**: Zero private resume content, secrets, or biometric inferences in source code or logs.

---

## 2. Phase-by-Phase Roadmap

### Phase 1: Foundation, Scaffolding & Database (Parts 01 – 06)
- **Part 01 — Repository reconnaissance and baseline snapshot**
  - *Status*: **COMPLETE**
  - *Deliverable*: Baseline runtime discovery (Python 3.13, Node 22, npm 10), workspace confirmation, and risk analysis.
- **Part 02 — Freeze MVP scope and architecture**
  - *Status*: **COMPLETE**
  - *Deliverable*: `docs/architecture.md` and `docs/implementation_plan.md` defining system boundaries, data flows, and deferred scope.
- **Part 03 — Create or align project scaffolding**
  - *Status*: **COMPLETE**
  - *Objective*: Build directory layout (`backend/`, `frontend/`, `docs/`, `tests/`, `evaluation/`), `.gitignore`, `.env.example`, and baseline root `README.md`.
  - *Acceptance*: Directory structure clean, build artifacts and secrets ignored, non-secret placeholder variables defined.
- **Part 04 — Environment and dependency reproducibility**
  - *Status*: **COMPLETE**
  - *Objective*: Pin backend (`requirements.txt` / `pyproject.toml`) and frontend (`package.json`) dependencies with Python 3.13 compatibility. Define Pydantic settings module.
  - *Acceptance*: Reproducible virtual environment and package installation without broken C-extension builds.
- **Part 05 — Backend app entry point and health checks**
  - *Status*: **COMPLETE**
  - *Objective*: FastAPI bootstrap, CORS configuration, structured exception handlers, `/api/v1/health` endpoint, and health check test.
  - *Acceptance*: Backend boots cleanly, returns JSON health payload, handles CORS from configured origins.
- **Part 06 — Database schema and migrations**
  - *Status*: **COMPLETE**
  - *Objective*: SQLAlchemy 2.0 declarative models (`users`, `profiles`, `resumes`, `skills`, `jobs`, `questions`, `attempts`, `interviews`), Alembic configuration, initial migration.
  - *Acceptance*: Migrations apply cleanly, foreign keys, unique constraints, and indices properly established.

---

### Phase 2: Authentication, Profile & Resume Parsing (Parts 07 – 11)
- **Part 07 — Authentication and session security**
  - *Status*: **COMPLETE**
  - *Objective*: User registration, bcrypt password hashing, JWT creation/validation, and `/api/v1/auth/me` endpoint.
  - *Acceptance*: Passwords never stored in plaintext, expired/invalid tokens rejected with 401, duplicate emails rejected with 400.
- **Part 08 — Onboarding, profile and target role**
  - *Status*: **COMPLETE**
  - *Objective*: User profile CRUD, target role configuration (defaults: Junior Python Developer, Entry-Level Data/ML Analyst).
  - *Acceptance*: User ownership enforced; onboarding copy free of hiring guarantee claims.
- **Part 09 — Secure resume upload endpoint**
  - *Status*: **COMPLETE**
  - *Objective*: Multipart file upload for PDF and DOCX, MIME/extension verification, private file storage outside web root using UUID keys.
  - *Acceptance*: Rejection of invalid types, oversized files (>5MB), and unauthenticated access.
- **Part 10 — PDF/DOCX text extraction**
  - *Status*: **COMPLETE**
  - *Objective*: Deterministic text extraction using `pypdf`/`pdfplumber` and `python-docx`. Graceful error handling for scanned/image-only PDFs.
  - *Acceptance*: Unit tests on synthetic documents succeed; scanned PDFs return actionable warnings rather than fake extracted text.
- **Part 11 — Resume sections, skills and evidence**
  - *Status*: **COMPLETE**
  - *Objective*: Section segmentation (education, experience, projects, skills), canonical skill dictionary mapping with aliases, and evidence snippet tagging.
  - *Acceptance*: Extracted skills linked to exact source sentences; user can add, edit, or remove skills with persistence.

---

### Phase 3: Job Intake, Explainable Matching & Evaluation (Parts 12 – 16)
- **Part 12 — Job description intake and management**
  - *Status*: **COMPLETE**
  - *Objective*: Authenticated CRUD for job descriptions, required vs preferred skill parsing, and synthetic demo job fixtures.
  - *Acceptance*: Jobs stored with provenance; manual skill requirement editing supported.
- **Part 13 — Lexical matching baseline**
  - *Status*: **COMPLETE**
  - *Objective*: Deterministic TF-IDF cosine similarity and normalized skill overlap ranker.
  - *Acceptance*: Deterministic, explainable matching output without external API calls.
- **Part 14 — Optional semantic similarity with safe fallback**
  - *Status*: **COMPLETE**
  - *Objective*: Lazy-loaded sentence embedding adapter with transparent fallback to lexical baseline when unavailable.
  - *Acceptance*: System starts without model download; fallback mode visibly flagged in API response.
- **Part 15 — Hybrid ranking and explainable results**
  - *Status*: **COMPLETE**
  - *Objective*: Weighted combination (0.50 required skill coverage + 0.30 semantic similarity + 0.20 preferred skill coverage), gap analysis, learning recommendations.
  - *Acceptance*: Breakdown of component scores; clear disclaimer that score represents text alignment, not hiring chance.
- **Part 16 — Matching evaluation dataset and notebook**
  - *Objective*: Frozen synthetic evaluation dataset, evaluation script computing Recall@K, MRR, and nDCG@K.
  - *Acceptance*: 100% reproducible metrics on frozen data; no fabricated benchmark numbers.

---

### Phase 4: Diagnostic Practice, Mastery & Recommendation (Parts 17 – 22)
- **Part 17 — Question bank model and curated seed content**
  - *Objective*: Tagged question bank (topic, difficulty, prompt, type, answer key, explanation) with curated synthetic technical questions.
  - *Acceptance*: Seed content easily extensible, questions strictly separated from user attempts.
- **Part 18 — Diagnostic practice API**
  - *Objective*: Diagnostic session initiation returning questions across core topics without leaking answer keys.
  - *Acceptance*: Answer keys withheld until submission; session ownership strictly checked.
- **Part 19 — Attempt recording and grading**
  - *Objective*: Submission endpoint, idempotent grading for objective questions, attempt persistence.
  - *Acceptance*: Correctness reflects actual answer keys; duplicate submissions prevented from double-counting.
- **Part 20 — Transparent mastery estimation**
  - *Objective*: Recent-weighted mastery scoring per topic (0–100) with difficulty scaling and reason codes.
  - *Acceptance*: Formulas fully explainable and deterministic; bounded [0, 100].
- **Part 21 — Next-question selection and study plan**
  - *Objective*: Rule-based adaptive recommender targeting weak topics (<60% mastery) and unpracticed areas.
  - *Acceptance*: Actionable recommendation reasons provided for every question.
- **Part 22 — Progress API and dashboard aggregates**
  - *Objective*: Aggregation endpoints for topic mastery trends, attempt history, and practice streaks.
  - *Acceptance*: Zero-state handling for new users; clean isolation across users.

---

### Phase 5: Mock Interview & Rubric-Based Coaching (Parts 23 – 27)
- **Part 23 — Mock interview session workflow**
  - *Objective*: Typed technical interview session lifecycle: creation, question prompt delivery, answer submission, session review.
  - *Acceptance*: Works entirely with typed answers without voice APIs or camera requirements.
- **Part 24 — Rubric-based feedback service**
  - *Objective*: Five-dimension rubric evaluation (Relevance, Technical Correctness, Completeness, Structure, Use of Examples).
  - *Acceptance*: Concrete quotes from user answers cited as evidence; actionable coaching advice returned.
- **Part 25 — Optional LLM provider adapter and prompt safety**
  - *Objective*: Isolated LLM adapter with schema validation, timeouts, prompt-injection guards, and deterministic fallback.
  - *Acceptance*: Missing API keys trigger clean fallback; prompt injection in inputs cannot compromise system prompts.
- **Part 26 — Interview feedback quality checks and audit trail**
  - *Objective*: Rubric versioning, synthetic edge-case answer fixtures, score bounds auditing.
  - *Acceptance*: Audit logging without persisting sensitive personal data.
- **Part 27 — Optional speech transcription (Deferred)**
  - *Objective*: Speech-to-text adapter marked optional; MVP defaults to typed mock interviews.
  - *Acceptance*: Application remains 100% functional when audio features are inactive.

---

### Phase 6: Frontend Development (Parts 28 – 35)
- **Part 28 — Frontend design system and app shell**
  - *Objective*: Accessible layout, responsive shell, typography, color tokens, and navigation.
- **Part 29 — Frontend authentication and onboarding screens**
  - *Objective*: Registration, login, target role selection, form validation, and token persistence.
- **Part 30 — Main dashboard interface**
  - *Objective*: Metric cards, topic mastery bars, next recommended practice action, and empty states.
- **Part 31 — Resume workspace UI**
  - *Objective*: Upload dropzone, parsing status, editable skill chips, and evidence snippet drawers.
- **Part 32 — Job matching UI**
  - *Objective*: Job entry, requirement review, match score visualization, and skill gap cards.
- **Part 33 — Practice room UI**
  - *Objective*: Question viewer, optional timer, answer submission, explanation modal, and next recommendation card.
- **Part 34 — Mock interview UI**
  - *Objective*: Typed interview room, answer editor, real-time submission, and rubric feedback breakdown.
- **Part 35 — Progress and export UI**
  - *Objective*: Topic mastery trends, attempt history table, and user data export/deletion controls.

---

### Phase 7: End-to-End Integration & Security (Parts 36 – 37)
- **Part 36 — End-to-end integration and API contract audit**
  - *Objective*: Contract alignment between frontend TypeScript types and backend Pydantic schemas across all user journeys.
- **Part 37 — Security, privacy, accessibility and regression suite**
  - *Objective*: Targeted audit for broken access control, CORS, secret leakage, OWASP Top 10, WCAG 2.1 AA accessibility checks.

---

### Phase 8: Evaluation, Deployment & Viva Readiness (Parts 38 – 40)
- **Part 38 — Final ML evaluation, error analysis and report artifacts**
  - *Objective*: Reproducible evaluation report with Recall@K, MRR, nDCG@K on frozen test fixtures, error analysis, and model cards.
- **Part 39 — Deployment readiness and demo environment**
  - *Objective*: Production build verification, docker/compose configuration, demo seed scripts, deployment documentation.
- **Part 40 — Release gate, documentation and viva rehearsal**
  - *Objective*: Comprehensive release checklist, live demo runbook, architectural viva prep, and finalized README.

---

## 3. Progress Tracking & Status Matrix

| Part | Title | Status | Evidence / Verification Notes |
| :---: | :--- | :---: | :--- |
| **01** | Repository reconnaissance & baseline snapshot | **PASS** | Empty workspace confirmed; runtimes recorded (Py 3.13.4, Node 22.16.0, npm 10.9.2). |
| **02** | Freeze MVP scope and architecture | **PASS** | `docs/architecture.md` & `docs/implementation_plan.md` created without conflicting stacks. |
| **03** | Create or align project scaffolding | **PASS** | Directory layout created, `.gitignore`, `.env.example`, and directory READMEs established. |
| **04** | Environment & dependency reproducibility | **PASS** | Dependencies pinned for Python 3.13; Pydantic settings module and tests passing. |
| **05** | Backend app entry point & health checks | **PASS** | FastAPI entry point, structured error handling, CORS, live health probe passing (13/13 tests). |
| **06** | Database schema & migrations | **PASS** | SQLAlchemy 2.0 entities, Alembic reversible migrations, constraint & cascade tests passing (19/19 tests). |
| **07** | Authentication & session security | **PASS** | Registration, bcrypt hashing, JWT issuance & validation, protected routes passing (31/31 tests). |
| **08** | Onboarding, profile & target role | **PASS** | Profile CRUD, role presets, onboarding disclosure, user ownership isolation passing (38/38 tests). |
| **09** | Secure resume upload endpoint | **PASS** | PDF/DOCX magic-byte validation, UUID storage isolation, size limits, ownership checks passing (47/47 tests). |
| **10** | PDF/DOCX text extraction | **PASS** | Deterministic extraction with pypdf/docx, scanned detection, encrypted handling, line preservation (57/57 tests). |
| **11** | Resume sections, skills & evidence | **PASS** | Section segmentation, taxonomy normalization, evidence linking, user skill CRUD passing (63/63 tests). |
| **12** | Job description intake & management | **PASS** | Auto-extraction, explicit overrides, demo seed, ownership isolation passing (75/75 tests). |
| **13** | Lexical matching baseline | **PASS** | TF-IDF cosine similarity, skill gap breakdown, coverage analysis passing (86/86 tests). |
| **14** | Optional semantic similarity with fallback | **PASS** | Lazy-load SentenceTransformers, transparent lexical fallback, mode status API passing (94/94 tests). |
| **15** | Hybrid ranking & explainable results | **PASS** | Hybrid score weighting, evidence snippet citations, learning recommendations passing (97/97 tests). |
| **16** | Matching evaluation dataset & notebook | **PASS** | Frozen benchmark dataset, MRR/Recall/nDCG evaluation harness, notebook passing (107/107 tests). |
| **17** | Question bank model & curated seed content | **PASS** | Curated 25 MCQ fixtures across 5 domains, answer leakage guards, topic taxonomy (120/120 tests). |
| **18** | Diagnostic practice API | **PASS** | Practice session lifecycle, progressive prompt delivery, answer leakage guards, ownership isolation (126/126 tests). |
| **19** | Attempt recording & grading | **PASS** | Deterministic objective grading, immediate educational feedback, history & stats tracking (135/135 tests). |
| **20** | Transparent mastery estimation | **PASS** | Exponential decay (gamma=0.85), difficulty scaling, reason codes, audit breakdown (146/146 tests). |
| **21** | Next-question selection & study plan | **PASS** | Rule-based adaptive selection, structured study plan roadmap, recommendation audits (152/152 tests). |
| **22** | Progress API & dashboard aggregates | **PASS** | Streak calculation, 14-day activity telemetry, placement readiness index, topic mastery status cards (159/159 tests). |
| **23** | Mock interview session workflow | **PASS** | Typed interview sessions, curated question catalog, response submissions, session state transitions, ownership isolation (176/176 tests). |
| **24** | Rubric-based feedback service | **PASS** | 5-dimension rubric engine, positive quote citations, concept coverage partitioning, feedback endpoint (189/189 tests). |
| **25** | Optional LLM provider adapter & safety | **PASS** | Adapter pattern, prompt injection sanitizer, output score bounding, resilient fallback, provider telemetry (198/198 tests). |
| **26** | Interview feedback quality & audit trail | **PASS** | Immutable audit table, prompt injection tracking, fallback reasons, quality reporting, zero drift (207/207 tests). |
| **27** | Optional speech transcription | **DEFERRED** | Explicit non-goal per product specification; typed-first interview experience complete and accessible without audio dependencies. |
| **28** | Frontend design system & app shell | **PASS** | CSS design tokens, responsive AppShell, React Router foundation, accessible alerts, ethical disclosures (Typecheck & Vite build 1592 modules 0 errors). |
| **29** | Frontend auth & onboarding screens | **PASS** | Validated login, register with strength meter, mandatory statutory disclosure checkbox, role onboarding wizard, and frontend-backend contract tests (211/211 passing tests, Vite build 1593 modules). |
| **30** | Main dashboard interface | **PASS** | Live telemetry, streak counters, 4-factor readiness breakdown, next-action card, topic mastery cards, 14-day activity chart (211/211 passing tests, Vite build 1593 modules). |
| **31** | Resume workspace UI | **PASS** | Drag-drop PDF/DOCX uploader, section segmentation viewer/editor, categorized skill taxonomy pills, evidence inspector, manual correction (211/211 passing tests, Vite build 1593 modules). |
| **32** | Job matching UI | **PASS** | Resume-job alignment matrix, batch ranking, score decomposition, skill gap badges, remediation recommendations, custom job intake (211/211 passing tests, Vite build 1593 modules). |
| **33** | Practice room UI | **PASS** | Interactive MCQ studio, topic/adaptive launcher, progressive prompt delivery, instant objective grading, pedagogical feedback, mastery tracking (211/211 passing tests, Vite build 1593 modules). |
| **34** | Mock interview UI | **PASS** | Typed interview studio, STAR technique helper, 5-dimension rubric breakdown, verbatim quote evidence, concept coverage matrix (211/211 passing tests, Vite build 1593 modules). |
| **35** | Progress & export UI | **PASS** | Top telemetry stats, topic mastery bars, step-by-step decay math audit modal, diagnostic attempt history table, AI evaluation audit log, quality & fairness report, JSON data export & data erasure controls (211/211 passing tests, Vite build 1593 modules). |
| **36** | End-to-end integration & contract audit | **PASS** | Full candidate lifecycle integration test (registration -> resume upload & extraction -> skill confirmation -> job intake -> explainable matching -> leak-proof practice -> deterministic grading -> mastery decay audit -> mock interview & rubric evaluation -> AI audit log -> dashboard telemetry -> GDPR export), multi-user boundary isolation, and 1:1 frontend TypeScript contract verification (215/215 passing backend tests, Vite build 1593 modules). |
| **37** | Security, privacy, accessibility & regression | **PASS** | Automated security hardening audit (OWASP Top 10, security headers middleware, strict CORS validation, zero hash/path secret leakage, SQL injection & XSS neutralization, adversarial prompt injection detection & audit logging, BOLA / IDOR isolation, statutory ethical disclaimers across all scoring engines), WCAG 2.1 AA accessibility compliance, and full 27-file regression suite (228/228 passing backend tests in 58.85s, Vite build 1593 modules 0 errors). |
| **38** | Final ML evaluation & report artifacts | NOT RUN | Scheduled. |
| **39** | Deployment readiness & demo environment | NOT RUN | Scheduled. |
| **40** | Release gate, documentation & viva prep | NOT RUN | Scheduled. |

