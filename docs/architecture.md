# CareerPilot AI — System Architecture Specification

## 1. Executive Summary & Product Target
**CareerPilot AI** is an intelligent, evidence-backed placement preparation platform designed for students and fresh graduates. The system unifies five core preparation workflows into an explainable, modular monolith:
1. **Resume Ingestion & Evidence-Based Extraction**: Deterministic text parsing from PDF/DOCX resumes with editable extraction fields and traceable text evidence snippets.
2. **Explainable Job Matching**: Transparent skill-gap analysis combining required skill coverage, semantic relevance, and preferred skill coverage with component-level score breakdowns.
3. **Tagged Diagnostic & Adaptive Practice**: Curated question bank tagged by topic and difficulty, paired with a deterministic recent-weighted mastery heuristic and explainable next-question recommendations.
4. **Structured Mock Interviews with Rubric Coaching**: Typed-first technical interviews evaluated against a five-dimension rubric (Relevance, Technical Correctness, Completeness, Structure, Use of Examples) citing specific answer evidence.
5. **Progress Tracking & Reproducible Evaluation**: Auditable learner dashboards and an evaluation harness using frozen synthetic benchmark datasets to evaluate ranking and extraction performance.

### Non-Goals and Explicit Product Guardrails
- **No Hiring Guarantees**: CareerPilot AI provides content relevance scores and coaching guidance; it never claims to predict placement probability or guarantee hiring.
- **No Inferred Psychological or Biometric States**: The platform strictly refrains from inferring confidence, honesty, personality, intelligence, or emotional state from audio, video, or response timing.
- **Typed-First Primacy**: Audio transcription is an optional secondary convenience; the entire mock interview experience is fully accessible via typed text.
- **Zero Hallucinated Credentials**: The matching engine cannot invent candidate qualifications or resume details to improve match metrics.

---

## 2. High-Level Architectural Pattern: Modular Monolith

CareerPilot AI avoids microservices complexity and operational overhead by adopting a **Modular Monolith** architecture:

```
+-----------------------------------------------------------------------------------+
|                                  React 18+ SPA                                    |
|                      (TypeScript, Vite, Semantic HTML, CSS)                       |
+-----------------------------------------+-----------------------------------------+
                                          | HTTP / JSON (REST)
                                          v
+-----------------------------------------------------------------------------------+
|                               FastAPI Application                                 |
|                                                                                   |
|  +--------------------+  +--------------------+  +-----------------------------+  |
|  |    Auth & User     |  |   Resume Ingest    |  |    Job Intake & Matching    |  |
|  |  (JWT, Passwords)  |  |  (Parse, Evidence) |  |   (TF-IDF, Hybrid Ranker)   |  |
|  +--------------------+  +--------------------+  +-----------------------------+  |
|  +--------------------+  +--------------------+  +-----------------------------+  |
|  |  Practice Bank &   |  |   Mock Interview   |  |     Progress & Auditing     |  |
|  |  Adaptive Mastery  |  |  (Rubric Coaching) |  |    (Aggregates, Metrics)    |  |
|  +--------------------+  +--------------------+  +-----------------------------+  |
|                                                                                   |
|  Core Services & Adapters:                                                        |
|  - AI Provider Adapter: LLM client with deterministic rubric-based rule fallback  |
|  - Embedding Adapter: Lazy sentence-transformer with TF-IDF fallback              |
|  - Storage Abstraction: Local private storage with opaque UUID file keys          |
+-----------------------------------------+-----------------------------------------+
                                          | SQLAlchemy 2.0 / Alembic
                                          v
+-----------------------------------------------------------------------------------+
|                                 Relational Database                               |
|              (PostgreSQL in Production / SQLite for Test & Local Dev)             |
+-----------------------------------------------------------------------------------+
```

---

## 3. Technology Stack & Decision Matrix

| Layer | Selected Technology | Rationale | Alternatives Considered & Rejected |
| :--- | :--- | :--- | :--- |
| **Frontend Web** | React 18+ / TypeScript / Vite | Type safety, rapid HMR, component-driven design system, clean contract alignment with backend schemas. | Next.js (rejected: unnecessary SSR overhead for a private dashboard SPA), Plain JS (rejected: lack of schema safety). |
| **Backend API** | FastAPI (Python 3.13) | Native async, high throughput, automatic OpenAPI documentation, tight integration with Pydantic v2. | Django (rejected: heavier ORM/admin baggage), Flask (rejected: manual schema validation). |
| **Data Validation** | Pydantic v2 | Strict request/response serialization, typed contracts shared conceptually with frontend interfaces. | Marshmallow (slower, less type-hint native). |
| **Database ORM** | SQLAlchemy 2.0 | Explicit typing, mature migration path, cross-database support (PostgreSQL target + SQLite test fallback). | Tortoise ORM (smaller ecosystem), Raw SQL (higher security risk for migrations). |
| **Database Migrations**| Alembic | Version-controlled, reversible schema migrations compatible with SQLAlchemy. | Ad-hoc SQL scripts (rejected: unversioned, high regression risk). |
| **NLP Baseline** | scikit-learn | Deterministic, fast TF-IDF vectorizer and cosine similarity; zero API cost or external download dependency. | Complex LLM-only matching (rejected: unexplainable, high latency, non-deterministic). |
| **Semantic Matching**| Sentence-Transformers (Optional) | Semantic enhancement behind adapter interface; lazy-loaded. | Direct external vector DB (rejected: unnecessary operational overhead for MVP). |
| **AI Provider** | Provider-agnostic adapter | Pluggable LLM interface with strict timeout, retry, and deterministic rule-based fallback. | Direct vendor SDK lock-in (rejected: fragile, breaks without active credentials). |

---

## 4. Module Boundaries & Data Flow

### Module 1: Auth, User & Profile Management
- **Scope**: User registration, bcrypt password hashing, JWT issue/validation, onboarding profile setup (target role, preferred language, consent tracking).
- **Data Boundary**: Owns `users` and `profiles` tables.
- **Security Rule**: Every incoming request is authenticated via Bearer token; queries are strictly scoped to the authenticated user ID (`user_id = current_user.id`).

### Module 2: Resume Ingestion & Evidence Parsing
- **Scope**: Multipart upload of PDF/DOCX resumes, file signature validation (magic bytes), private storage outside the web root, deterministic text extraction, canonical skill mapping, and evidence snippet generation.
- **Data Boundary**: Owns `resumes`, `resume_skills`, and `skill_dictionary` tables.
- **Transparency Rule**: Extracted skills maintain a flag: `is_user_confirmed` vs `is_auto_extracted`. Users can add, modify, or delete skills.

### Module 3: Job Intake & Management
- **Scope**: Manual entry or structured intake of job descriptions (title, company, description, required skills, preferred skills, source provenance).
- **Data Boundary**: Owns `jobs` and `job_skills` tables.
- **Policy**: No unauthorized web scraping. Sample data is explicitly flagged as `is_synthetic = True`.

### Module 4: Job Matching & Explainability Engine
- **Scope**: Hybrid scoring calculation:
  $$\text{Match Score} = w_1 \cdot \text{ReqCoverage} + w_2 \cdot \text{SemanticSim} + w_3 \cdot \text{PrefCoverage}$$
  - Baseline hypothesis weights: $w_1 = 0.50$, $w_2 = 0.30$, $w_3 = 0.20$.
  - Fallback weights (when semantic model is unavailable): $w_1 = 0.70$, $w_2 = 0.00$, $w_3 = 0.30$.
- **Outputs**: Detailed breakdown showing matched required skills, matched preferred skills, missing skills, evidence quotes, and targeted learning recommendations. Never presented as a "hiring probability".

### Module 5: Tagged Practice & Mastery
- **Scope**: Curated question bank categorized by role, topic, and difficulty (Easy, Medium, Hard). Objective questions have deterministic answer keys; attempts are tracked with timestamps and correctness.
- **Mastery Heuristic**:
  $$\text{Topic Mastery} = \frac{\sum_{i=1}^N w_i \cdot c_i \cdot d_i}{\sum_{i=1}^N w_i \cdot d_i} \times 100$$
  where $c_i \in \{0, 1\}$ is correctness, $d_i$ is question difficulty weight (e.g. 1.0, 1.2, 1.5), and $w_i = \gamma^{N-i}$ represents recency decay ($\gamma = 0.85$).
- **Transparency Rule**: Reason codes accompany mastery levels (e.g., `RECENT_IMPROVEMENT`, `NEEDS_PRACTICE`, `NO_DATA`).

### Module 6: Adaptive Recommendation Service
- **Scope**: Deterministic recommendation algorithm that prioritizes:
  1. Unpracticed topics in the user's target role.
  2. Topics with mastery score $< 60\%$.
  3. Moderate difficulty questions to consolidate learning before advancing.
- **Transparency Rule**: Every recommendation provides a rationale (e.g., *"Recommended because your recent accuracy in SQL Joins is 40%"*).

### Module 7: Mock Interview & Rubric Feedback Engine
- **Scope**: Typed technical interview sessions. Questions generated from role-specific competency areas.
- **Rubric Dimensions**:
  1. *Relevance* (0–20): Did the response address the exact prompt?
  2. *Technical Correctness* (0–20): Are statements accurate, free of hallucinations or syntax misconceptions?
  3. *Completeness* (0–20): Did the answer cover critical edge cases and core concepts?
  4. *Structure* (0–20): Is the response logically organized (e.g. STAR method or systematic problem solving)?
  5. *Use of Examples* (0–20): Did the candidate cite concrete code, architectural choices, or scenario outcomes?
- **Total Rubric Score**: 0–100 scale, accompanied by explicit positive evidence quotes, missing key concepts, and constructive action items.

### Module 8: Progress & Evaluation Service
- **Scope**: Aggregation of learner activity across practice and interview sessions. Offline evaluation scripts for model ranking metrics (Recall@K, MRR, nDCG@K) using frozen datasets.

---

## 5. Error-Handling Policy & API Contract Standards

1. **Standard Error Envelope**: All API error responses adhere to a consistent JSON structure:
   ```json
   {
     "error": {
       "code": "RESOURCE_NOT_FOUND",
       "message": "The requested job description does not exist or you do not have permission to view it.",
       "details": []
     }
   }
   ```
2. **HTTP Status Code Discipline**:
   - `200 OK` / `201 Created` / `204 No Content` for successful requests.
   - `400 Bad Request` for invalid input parameters or schema failures.
   - `401 Unauthorized` for missing, expired, or invalid authentication tokens.
   - `403 Forbidden` for attempts to access records owned by another user.
   - `404 Not Found` when a requested entity does not exist.
   - `422 Unprocessable Entity` for Pydantic schema validation failures.
   - `503 Service Unavailable` with graceful degradation messages when optional third-party integrations fail.
3. **No Internal Leakage**: Stack traces, raw database error strings, and file path internals must never be returned to client responses or stored in user-facing logs.

---

## 6. Security, Privacy & Data Retention Architecture

1. **Ownership Enforcement**: No endpoint permits direct primary key querying without verifying `user_id == current_user.id`.
2. **File Storage Isolation**:
   - Uploaded resumes are named with random UUIDs and saved in a private storage directory outside the static web server path.
   - Direct file downloads are served via authenticated streaming responses checking record ownership.
   - MIME validation and extension white-listing (`.pdf`, `.docx`) are enforced server-side.
3. **Password Security**: Passwords hashed using bcrypt with salt rounds $\ge 12$. No plaintext passwords stored or logged.
4. **Secret Management**: All keys, JWT secrets, and database credentials originate from environment variables. No `.env` files committed.
5. **Right to Erasure & Data Retention**:
   - Explicit user endpoint to delete account, profile, uploaded resumes, and interview attempts.
   - Hard deletion removes physical files from private storage and cascades through database records.

---

## 7. Explicitly Deferred / Optional Scope

The following features from the product blueprint are marked **Optional & Deferred** to guarantee MVP stability:
- **Speech-to-Text & Audio Feature Extraction**: Deferred to Part 27 as an optional adapter. The MVP operates 100% on typed interaction.
- **Bayesian Knowledge Tracing (BKT)**: Replaced in the MVP by the transparent recent-weighted accuracy heuristic. BKT remains a future enhancement.
- **Cohort & Cross-Student Ranking**: Deferred. The MVP focuses exclusively on single-user mastery and personalized coaching.
- **Live Video / Proctoring / Appearance Analysis**: Strictly prohibited per non-negotiable guidelines.

---

## 8. Environment Assumptions & Unverified Decisions

- **Host Environment**: Windows 11 with Python 3.13.4 and Node.js v22.16.0 / npm 10.9.2.
- **Database Engine**: While PostgreSQL is the target production engine, the local environment currently lacks `psql` and `docker`. The architecture mandates a configurable `DATABASE_URL` that defaults to SQLite (`sqlite:///./careerpilot.db`) for local developer testing and runs seamlessly on PostgreSQL when configured in deployment.
- **AI Credentials**: No external paid API key is required to build, test, or demonstrate the application. All core functionality operates with deterministic local heuristics.

