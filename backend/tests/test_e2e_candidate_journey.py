"""End-to-End candidate journey integration test and API contract audit.

Part 36: Validates the entire learner lifecycle through real API calls:
1. Registration -> Login -> Onboarding & Profile Configuration.
2. Synthetic PDF Resume Upload -> Section Segmentation -> Skill Taxonomy & Evidence Linking.
3. Custom Skill Addition -> Confirmation Toggle.
4. Job Description Intake & Synthetic Benchmark Seeding.
5. Explainable Hybrid Matching -> Decomposition Scores -> Gap Analysis & Disclaimers.
6. Diagnostic Practice Session -> Progressive Prompt Delivery (Leak-Proof).
7. Deterministic MCQ Grading -> Immediate Educational Feedback.
8. Mastery Calculation -> Mathematical Decay Audit (gamma=0.85).
9. Adaptive Recommendation -> Weak Topic Remediation.
10. Mock Interview Session -> Typed Candidate Answer -> 5-Dimension Rubric Coaching.
11. AI Evaluation Auditing -> Quality & Latency Report.
12. Learner Progress Dashboard -> Streak Telemetry -> Placement Readiness Index.
13. GDPR Candidate Data Export Bundle.
14. Multi-Tenant Boundary & Ownership Isolation.
15. Strict TypeScript Frontend Contract Field Alignment.
"""

import io
import json
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.deps import get_db
from app.db.base import Base
from app.main import app
from app.models import Question
from app.services.question_service import seed_questions
from app.services.semantic_service import MockEmbeddingAdapter, semantic_manager


@event.listens_for(Engine, "connect")
def _set_sqlite_pragma(dbapi_connection, connection_record):
    """Enforce foreign key constraints in SQLite test engine."""
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


@pytest.fixture
def test_db():
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
    seed_questions(session)  # Seed curated benchmark MCQs into test DB
    yield session

    session.close()
    Base.metadata.drop_all(bind=test_engine)
    app.dependency_overrides.pop(get_db, None)


@pytest.fixture
def client(test_db):
    """Provide a TestClient connected to the overridden test database."""
    return TestClient(app, base_url="http://127.0.0.1")


@pytest.fixture(autouse=True)
def cleanup_semantic_provider():
    """Ensure the default semantic provider is restored after each test."""
    yield
    semantic_manager.reset_default_provider()


def _get_auth_token(client: TestClient, email: str, password: str = "SecurePassword123!") -> str:
    """Helper to register and login a test user, returning their access token."""
    client.post("/api/v1/auth/register", json={"email": email, "password": password})
    res = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    return res.json()["access_token"]


def _create_synthetic_text_pdf(lines: list[str]) -> bytes:
    """Build a minimal valid PDF containing extractable text streams."""
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


# ==============================================================================
# 1. Complete Candidate Journey End-to-End Test
# ==============================================================================

class TestCandidateJourneyE2E:
    """Exercises the complete end-to-end candidate preparation lifecycle."""

    def test_full_candidate_lifecycle(self, client: TestClient, test_db: Session):
        # ----------------------------------------------------------------------
        # Step 1: System Health & Provider Diagnostics
        # ----------------------------------------------------------------------
        health_res = client.get("/api/v1/health")
        assert health_res.status_code == 200
        health_data = health_res.json()
        assert health_data["status"] == "healthy"
        assert "version" in health_data

        status_res = client.get("/api/v1/interviews/provider/status")
        assert status_res.status_code == 200
        provider_data = status_res.json()
        assert "active_provider" in provider_data
        assert "fallback_adapter" in provider_data
        assert "is_available" in provider_data

        # ----------------------------------------------------------------------
        # Step 2: Candidate Registration & Login
        # ----------------------------------------------------------------------
        email = "alice_candidate@university.edu"
        password = "ComplexPassword2026!"

        reg_res = client.post("/api/v1/auth/register", json={"email": email, "password": password})
        assert reg_res.status_code == 201
        reg_data = reg_res.json()
        assert reg_data["email"] == email
        user_id = reg_data["id"]

        login_res = client.post("/api/v1/auth/login", json={"email": email, "password": password})
        assert login_res.status_code == 200
        token_data = login_res.json()
        token = token_data["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # ----------------------------------------------------------------------
        # Step 3: Onboarding & Profile Configuration
        # ----------------------------------------------------------------------
        roles_res = client.get("/api/v1/profile/roles")
        assert roles_res.status_code == 200
        roles = roles_res.json()
        assert len(roles) >= 2

        onboard_info = client.get("/api/v1/profile/onboarding-info").json()
        assert onboard_info["camera_or_mic_required"] is False
        assert len(onboard_info["disclaimers"]) >= 3

        put_prof = client.put(
            "/api/v1/profile",
            json={
                "target_role": "Junior Python Developer",
                "preferred_language": "en",
                "consent_analytics": True,
            },
            headers=headers,
        )
        assert put_prof.status_code == 200
        prof_data = put_prof.json()
        assert prof_data["target_role"] == "Junior Python Developer"

        # ----------------------------------------------------------------------
        # Step 4: Resume Upload & Parsing
        # ----------------------------------------------------------------------
        resume_lines = [
            "ALICE SMITH",
            "Junior Python Developer",
            "Professional Summary",
            "Enthusiastic software engineering student experienced in Python, FastAPI, and SQL backends.",
            "Technical Skills",
            "Languages: Python, JavaScript, SQL",
            "Frameworks: FastAPI, React",
            "Databases: PostgreSQL, SQLite",
            "Experience",
            "Backend Intern at TechCorp",
            "Engineered RESTful APIs with FastAPI and optimized PostgreSQL queries.",
            "Projects",
            "Placement Portal: Designed microservices using Python and Docker.",
            "Education",
            "B.Tech in Computer Science and Engineering",
        ]
        pdf_bytes = _create_synthetic_text_pdf(resume_lines)
        upload_res = client.post(
            "/api/v1/resumes/upload",
            files={"file": ("alice_cv.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
            headers=headers,
        )
        assert upload_res.status_code == 201
        resume_data = upload_res.json()
        resume_id = resume_data["id"]
        assert resume_data["id"] == resume_id
        assert resume_data["original_filename"] == "alice_cv.pdf"
        assert resume_data["parse_status"] in ("completed", "success", "warning")

        # ----------------------------------------------------------------------
        # Step 5: Resume Sections & Skill Confirmation
        # ----------------------------------------------------------------------
        sections_res = client.get(f"/api/v1/resumes/{resume_id}/sections", headers=headers)
        assert sections_res.status_code == 200
        sec_data = sections_res.json()
        assert "sections" in sec_data
        assert "skills" in sec_data

        skills_res = client.get(f"/api/v1/resumes/{resume_id}/skills", headers=headers)
        assert skills_res.status_code == 200
        skills_list = skills_res.json()
        assert len(skills_list) > 0

        # Confirm first skill
        target_skill = skills_list[0]
        skill_id = target_skill["id"]
        confirm_res = client.put(
            f"/api/v1/resumes/{resume_id}/skills/{skill_id}",
            json={"is_user_confirmed": True},
            headers=headers,
        )
        assert confirm_res.status_code == 200
        assert confirm_res.json()["is_user_confirmed"] is True

        # Add custom skill (Docker)
        add_skill_res = client.post(
            f"/api/v1/resumes/{resume_id}/skills",
            json={"skill_name": "Docker", "category": "devops"},
            headers=headers,
        )
        assert add_skill_res.status_code == 201
        assert add_skill_res.json()["canonical_name"].lower() == "docker"

        # ----------------------------------------------------------------------
        # Step 6: Job Catalog Intake & Demo Seed
        # ----------------------------------------------------------------------
        seed_job_res = client.post("/api/v1/jobs/seed-demo", headers=headers)
        assert seed_job_res.status_code == 200
        seed_data = seed_job_res.json()
        assert len(seed_data) >= 1

        # Create custom job description
        custom_job_res = client.post(
            "/api/v1/jobs",
            json={
                "title": "Backend Python Developer",
                "company": "Apex Cloud Systems",
                "description": "Seeking a Junior Python engineer proficient in Python, FastAPI, and Docker. PostgreSQL preferred.",
                "required_skills": ["python", "fastapi", "docker"],
                "preferred_skills": ["postgresql", "redis"],
            },
            headers=headers,
        )
        assert custom_job_res.status_code == 201
        job_id = custom_job_res.json()["id"]

        # ----------------------------------------------------------------------
        # Step 7: Explainable Job Matching & Skill Gap Analysis
        # ----------------------------------------------------------------------
        batch_res = client.post(
            f"/api/v1/matching/resumes/{resume_id}/batch",
            params={"use_semantic": False},
            headers=headers,
        )
        assert batch_res.status_code == 200
        batch_data = batch_res.json()
        assert batch_data["total_jobs_evaluated"] >= 1
        assert "disclaimer" in batch_data
        assert "predict" in batch_data["disclaimer"].lower() or "guarantee" in batch_data["disclaimer"].lower()

        # Detailed explainable match
        match_res = client.post(
            f"/api/v1/matching/resumes/{resume_id}/jobs/{job_id}",
            params={"use_semantic": False},
            headers=headers,
        )
        assert match_res.status_code == 200
        match_data = match_res.json()
        assert match_data["scores"]["overall_score"] > 0
        assert "required_coverage" in match_data["scores"]
        assert "tfidf_similarity" in match_data["scores"]
        assert "skill_gap" in match_data
        assert "python" in [s.lower() for s in match_data["skill_gap"]["matched_required"]]
        assert len(match_data["evidence"]) > 0
        assert "disclaimer" in match_data

        # ----------------------------------------------------------------------
        # Step 8: Diagnostic Practice Session & Progressive Delivery
        # ----------------------------------------------------------------------
        topics_res = client.get("/api/v1/practice/topics", headers=headers)
        assert topics_res.status_code == 200
        topics = topics_res.json()
        assert len(topics) >= 1

        session_res = client.post(
            "/api/v1/practice/sessions",
            json={"topic": "Python", "difficulty": "easy", "question_count": 2},
            headers=headers,
        )
        assert session_res.status_code == 201
        sess_data = session_res.json()
        practice_session_id = sess_data["session_id"]
        assert sess_data["status"] == "in_progress"

        # Security check: verify answer key is not leaked in question payloads
        for q in sess_data["questions"]:
            assert "answer_key" not in q
            assert "explanation" not in q

        # ----------------------------------------------------------------------
        # Step 9: MCQ Attempts & Immediate Deterministic Grading
        # ----------------------------------------------------------------------
        # Fetch question details from DB to test correct and incorrect attempts
        q_record = test_db.query(Question).filter(Question.topic == "Python").first()
        assert q_record is not None

        attempt_res = client.post(
            "/api/v1/practice/attempts",
            json={
                "question_id": q_record.id,
                "session_id": practice_session_id,
                "user_answer": q_record.answer_key,
                "duration_seconds": 15,
            },
            headers=headers,
        )
        assert attempt_res.status_code == 201
        attempt_data = attempt_res.json()
        assert attempt_data["is_correct"] is True
        assert attempt_data["score"] == 1.0
        assert attempt_data["correct_answer_key"] == q_record.answer_key
        assert len(attempt_data["explanation"]) > 5

        # Check stats aggregate
        stats_res = client.get("/api/v1/practice/attempts/stats", headers=headers)
        assert stats_res.status_code == 200
        stats = stats_res.json()
        assert stats["total_attempts"] >= 1
        assert stats["correct_attempts"] >= 1

        # ----------------------------------------------------------------------
        # Step 10: Topic Mastery & Recency Math Audit (gamma=0.85)
        # ----------------------------------------------------------------------
        mastery_res = client.get("/api/v1/practice/mastery", headers=headers)
        assert mastery_res.status_code == 200
        masteries = mastery_res.json()
        assert len(masteries["items"]) >= 1

        # Inspect mathematical audit for Python
        audit_res = client.get("/api/v1/practice/mastery/Python", headers=headers)
        assert audit_res.status_code == 200
        math_audit = audit_res.json()
        assert math_audit["topic"] == "Python"
        assert math_audit["decay_factor"] == 0.85
        assert math_audit["attempts_considered"] >= 1
        assert len(math_audit["contributions"]) >= 1
        assert "Mastery" in math_audit["formula_explanation"] or "sum" in math_audit["formula_explanation"]

        # ----------------------------------------------------------------------
        # Step 11: Adaptive Recommendations
        # ----------------------------------------------------------------------
        rec_res = client.get("/api/v1/practice/recommendations/study-plan", headers=headers)
        assert rec_res.status_code == 200
        study_plan = rec_res.json()
        assert "target_role" in study_plan
        assert "summary" in study_plan

        # ----------------------------------------------------------------------
        # Step 12: Mock Interview Lifecycle & Rubric Coaching
        # ----------------------------------------------------------------------
        cat_res = client.get("/api/v1/interviews/catalog")
        assert cat_res.status_code == 200
        catalog = cat_res.json()
        assert catalog["total_questions"] >= 5

        int_sess_res = client.post(
            "/api/v1/interviews/sessions",
            json={"role": "Backend Engineer", "competency": "System Design"},
            headers=headers,
        )
        assert int_sess_res.status_code == 201
        interview_session = int_sess_res.json()
        int_id = interview_session["id"]
        assert interview_session["status"] == "in_progress"

        # Submit technical response
        valid_answer = (
            "In designing this architecture, I apply the Single Responsibility Principle and partition "
            "the system into decoupled microservices. Communication occurs asynchronously using RabbitMQ "
            "message brokers for event ingestion, while synchronous operations use gRPC. To guarantee "
            "high availability, services are deployed across multiple availability zones behind an NGINX "
            "load balancer. Redis provides in-memory caching for read-heavy query patterns, reducing database "
            "load by 65%. PostgreSQL acts as the ACID-compliant primary datastore with automated replication."
        )
        submit_res = client.post(
            f"/api/v1/interviews/sessions/{int_id}/submit",
            json={"user_response": valid_answer, "duration_seconds": 140},
            headers=headers,
        )
        assert submit_res.status_code == 200
        submitted_data = submit_res.json()
        assert submitted_data["status"] in ("submitted", "completed")
        assert submitted_data["total_score"] is not None
        assert submitted_data["dimension_scores"] is not None

        # Fetch detailed rubric feedback
        feedback_res = client.get(f"/api/v1/interviews/sessions/{int_id}/feedback", headers=headers)
        assert feedback_res.status_code == 200
        feedback = feedback_res.json()
        assert feedback["total_score"] >= 0
        assert "relevance" in feedback["dimension_scores"]
        assert "technical_correctness" in feedback["dimension_scores"]
        assert "completeness" in feedback["dimension_scores"]
        assert "structure" in feedback["dimension_scores"]
        assert "use_of_examples" in feedback["dimension_scores"]
        assert "disclaimer" in feedback

        # ----------------------------------------------------------------------
        # Step 13: AI Evaluation Auditing & Quality Telemetry
        # ----------------------------------------------------------------------
        audits_res = client.get("/api/v1/interviews/audits", headers=headers)
        assert audits_res.status_code == 200
        audits = audits_res.json()
        assert audits["total"] >= 1
        latest_audit = audits["audits"][0]
        assert latest_audit["session_id"] == int_id
        assert latest_audit["evaluated_score"] is not None
        assert latest_audit["prompt_injection_flag"] is False

        quality_res = client.get("/api/v1/interviews/audits/quality-report", headers=headers)
        assert quality_res.status_code == 200
        quality = quality_res.json()
        assert quality["total_evaluations"] >= 1
        assert quality["compliance_rate"] == 1.0

        # ----------------------------------------------------------------------
        # Step 14: Learner Dashboard & Telemetry Aggregates
        # ----------------------------------------------------------------------
        dash_res = client.get("/api/v1/progress/dashboard", headers=headers)
        assert dash_res.status_code == 200
        dashboard = dash_res.json()
        assert dashboard["target_role"] == "Junior Python Developer"
        assert dashboard["streak_days"] >= 1
        assert dashboard["total_attempts"] >= 1
        assert "readiness" in dashboard
        assert dashboard["readiness"]["overall_readiness_score"] >= 0
        assert dashboard["readiness"]["readiness_level"] in (
            "beginner", "developing", "placement_ready", "interview_ready"
        )
        assert "disclaimer" in dashboard["readiness"]
        assert len(dashboard["topic_masteries"]) >= 1
        assert "next_action" in dashboard

        streak_res = client.get("/api/v1/progress/streak", headers=headers)
        assert streak_res.status_code == 200
        streak = streak_res.json()
        assert streak["current_streak_days"] >= 1

        readiness_res = client.get("/api/v1/progress/readiness", headers=headers)
        assert readiness_res.status_code == 200
        readiness = readiness_res.json()
        assert readiness["overall_readiness_score"] >= 0
        assert "disclaimer" in readiness

        # ----------------------------------------------------------------------
        # Step 15: GDPR-Style Data Export Verification
        # ----------------------------------------------------------------------
        candidate_data_bundle = {
            "exported_at": "2026-11-06T12:00:00Z",
            "user_account": client.get("/api/v1/auth/me", headers=headers).json(),
            "candidate_profile": prof_data,
            "resumes": client.get("/api/v1/resumes", headers=headers).json(),
            "practice_attempts": client.get("/api/v1/practice/attempts", headers=headers).json(),
            "topic_masteries": masteries,
            "mock_interviews": client.get("/api/v1/interviews/sessions", headers=headers).json(),
            "evaluation_audits": audits,
        }
        json_bundle = json.dumps(candidate_data_bundle)
        assert len(json_bundle) > 500
        assert "alice_candidate@university.edu" in json_bundle
        assert "alice_cv.pdf" in json_bundle


# ==============================================================================
# 2. Multi-Tenant User Isolation & Boundary Protection Tests
# ==============================================================================

class TestMultiUserBoundaryIsolation:
    """Verifies strict data isolation across distinct users."""

    def test_cross_user_isolation(self, client: TestClient):
        # Create User A
        token_a = _get_auth_token(client, "user_a@example.com")
        headers_a = {"Authorization": f"Bearer {token_a}"}

        # Create User B
        token_b = _get_auth_token(client, "user_b@example.com")
        headers_b = {"Authorization": f"Bearer {token_b}"}

        # User A uploads a resume
        pdf_bytes = _create_synthetic_text_pdf(["User A Confidential CV", "Python, SQL"])
        upload_a = client.post(
            "/api/v1/resumes/upload",
            files={"file": ("cv_a.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
            headers=headers_a,
        )
        assert upload_a.status_code == 201
        resume_a_id = upload_a.json()["id"]

        # User B attempts to access User A's resume -> 404
        b_get_res = client.get(f"/api/v1/resumes/{resume_a_id}", headers=headers_b)
        assert b_get_res.status_code == 404

        # User B attempts to edit User A's sections -> 404
        b_put_sec = client.put(
            f"/api/v1/resumes/{resume_a_id}/sections",
            json={"sections": {"summary": "Hacked content"}},
            headers=headers_b,
        )
        assert b_put_sec.status_code == 404

        # User B attempts to delete User A's resume -> 404
        b_del_res = client.delete(f"/api/v1/resumes/{resume_a_id}", headers=headers_b)
        assert b_del_res.status_code == 404

        # User A creates a practice session
        session_a = client.post(
            "/api/v1/practice/sessions",
            json={"topic": "Python", "question_count": 2},
            headers=headers_a,
        ).json()
        sess_a_id = session_a["session_id"]

        # User B cannot access User A's practice session -> 404
        b_get_sess = client.get(f"/api/v1/practice/sessions/{sess_a_id}", headers=headers_b)
        assert b_get_sess.status_code == 404

        # User A creates an interview session
        int_a = client.post(
            "/api/v1/interviews/sessions",
            json={"role": "Backend Engineer"},
            headers=headers_a,
        ).json()
        int_a_id = int_a["id"]

        # User B cannot view User A's interview session -> 404
        b_get_int = client.get(f"/api/v1/interviews/sessions/{int_a_id}", headers=headers_b)
        assert b_get_int.status_code == 404

        # User B cannot submit an answer to User A's interview session -> 404
        b_sub_int = client.post(
            f"/api/v1/interviews/sessions/{int_a_id}/submit",
            json={"user_response": "Malicious response submitted by unauthorized user."},
            headers=headers_b,
        )
        assert b_sub_int.status_code == 404

        # User B cannot read User A's interview feedback -> 404
        b_feed_int = client.get(f"/api/v1/interviews/sessions/{int_a_id}/feedback", headers=headers_b)
        assert b_feed_int.status_code == 404

    def test_unauthenticated_requests_rejected(self, client: TestClient):
        """Unauthenticated requests to protected endpoints return 401 Unauthorized."""
        protected_endpoints = [
            ("GET", "/api/v1/auth/me"),
            ("GET", "/api/v1/profile"),
            ("PUT", "/api/v1/profile"),
            ("GET", "/api/v1/resumes"),
            ("POST", "/api/v1/jobs"),
            ("POST", "/api/v1/practice/sessions"),
            ("GET", "/api/v1/practice/mastery"),
            ("POST", "/api/v1/interviews/sessions"),
            ("GET", "/api/v1/interviews/audits"),
            ("GET", "/api/v1/progress/dashboard"),
            ("GET", "/api/v1/progress/streak"),
            ("GET", "/api/v1/progress/readiness"),
        ]

        for method, endpoint in protected_endpoints:
            if method == "GET":
                resp = client.get(endpoint)
            elif method == "PUT":
                resp = client.put(endpoint, json={})
            else:
                resp = client.post(endpoint, json={})
            assert resp.status_code == 401, f"Expected 401 for unauthenticated {method} {endpoint}, got {resp.status_code}"


# ==============================================================================
# 3. API Contract Schema Alignment Verification
# ==============================================================================

class TestApiContractSchemaAlignment:
    """Verifies that API output JSON properties align 1:1 with frontend TypeScript interfaces."""

    def test_frontend_contract_key_presence(self, client: TestClient, test_db: Session):
        token = _get_auth_token(client, "contract_validator@example.com")
        headers = {"Authorization": f"Bearer {token}"}

        # 1. User & Auth contract: User, TokenResponse
        me_data = client.get("/api/v1/auth/me", headers=headers).json()
        for k in ["id", "email", "is_active", "is_verified", "created_at"]:
            assert k in me_data, f"Missing key '{k}' in User schema"

        # 2. Profile & OnboardingDisclosure contract
        prof_data = client.get("/api/v1/profile", headers=headers).json()
        for k in ["id", "user_id", "target_role", "preferred_language", "consent_analytics", "created_at", "updated_at"]:
            assert k in prof_data, f"Missing key '{k}' in Profile schema"

        onboard_data = client.get("/api/v1/profile/onboarding-info").json()
        for k in ["purpose", "disclaimers", "data_retention_policy", "camera_or_mic_required", "supported_roles"]:
            assert k in onboard_data, f"Missing key '{k}' in OnboardingDisclosure schema"

        # 3. Resume & ResumeSkill contract
        pdf_bytes = _create_synthetic_text_pdf(["Testing Candidate", "Python, FastAPI"])
        upload_data = client.post(
            "/api/v1/resumes/upload",
            files={"file": ("contract_test.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
            headers=headers,
        ).json()
        for k in ["id", "original_filename", "file_size_bytes", "mime_type", "parse_status", "created_at"]:
            assert k in upload_data, f"Missing key '{k}' in Resume schema"

        resume_id = upload_data["id"]
        sec_data = client.get(f"/api/v1/resumes/{resume_id}/sections", headers=headers).json()
        for k in ["resume_id", "sections", "skills"]:
            assert k in sec_data, f"Missing key '{k}' in ResumeSectionsResponse schema"

        # 4. Job contract: Job, JobListResponse
        job_data = client.post(
            "/api/v1/jobs",
            json={"title": "Test Engineer", "description": "Needs Python and Pytest."},
            headers=headers,
        ).json()
        for k in ["id", "title", "description", "is_synthetic", "is_active", "required_skills", "preferred_skills"]:
            assert k in job_data, f"Missing key '{k}' in Job schema"

        # 5. Matching contract: BatchMatchResponse, LexicalMatchResponse
        batch_data = client.post(f"/api/v1/matching/resumes/{resume_id}/batch", headers=headers).json()
        for k in ["resume_id", "total_jobs_evaluated", "matches", "disclaimer"]:
            assert k in batch_data, f"Missing key '{k}' in BatchMatchResponse schema"

        match_data = client.post(f"/api/v1/matching/resumes/{resume_id}/jobs/{job_data['id']}", headers=headers).json()
        for k in ["resume_id", "job_id", "job_title", "scores", "skill_gap", "evidence", "recommendations", "disclaimer"]:
            assert k in match_data, f"Missing key '{k}' in LexicalMatchResponse schema"
        for k in ["required_coverage", "preferred_coverage", "tfidf_similarity", "overall_score"]:
            assert k in match_data["scores"], f"Missing key '{k}' in MatchScoreBreakdown schema"
        for k in ["matched_required", "missing_required", "matched_preferred", "missing_preferred"]:
            assert k in match_data["skill_gap"], f"Missing key '{k}' in SkillGapBreakdown schema"

        # 6. Practice contract: PracticeSession, AttemptFeedback, TopicMastery, MasteryCalculationExplanation
        sess_data = client.post(
            "/api/v1/practice/sessions",
            json={"topic": "Python", "question_count": 2},
            headers=headers,
        ).json()
        for k in ["session_id", "topic", "status", "total_questions", "current_index", "questions"]:
            assert k in sess_data, f"Missing key '{k}' in PracticeSession schema"

        q_first = sess_data["questions"][0]
        for k in ["id", "topic", "difficulty", "prompt", "options"]:
            assert k in q_first, f"Missing key '{k}' in QuestionPublic schema"

        q_record = test_db.query(Question).filter(Question.topic == "Python").first()
        attempt_data = client.post(
            "/api/v1/practice/attempts",
            json={"question_id": q_record.id, "user_answer": q_record.answer_key, "duration_seconds": 10},
            headers=headers,
        ).json()
        for k in ["question_id", "user_answer", "is_correct", "score", "correct_answer_key", "explanation"]:
            assert k in attempt_data, f"Missing key '{k}' in AttemptFeedback schema"

        audit_data = client.get("/api/v1/practice/mastery/Python", headers=headers).json()
        for k in ["topic", "mastery_score", "decay_factor", "attempts_considered", "contributions", "formula_explanation"]:
            assert k in audit_data, f"Missing key '{k}' in MasteryCalculationExplanation schema"

        # 7. Mock Interview contract: InterviewSession, RubricFeedback, InterviewAuditOut, InterviewQualityReport
        cat_data = client.get("/api/v1/interviews/catalog").json()
        for k in ["total_questions", "roles", "competencies", "questions"]:
            assert k in cat_data, f"Missing key '{k}' in InterviewCatalogResponse schema"

        int_data = client.post("/api/v1/interviews/sessions", json={}, headers=headers).json()
        for k in ["id", "role", "competency", "question_text", "status", "disclaimer", "created_at"]:
            assert k in int_data, f"Missing key '{k}' in InterviewSession schema"

        sub_data = client.post(
            f"/api/v1/interviews/sessions/{int_data['id']}/submit",
            json={"user_response": "Here is my comprehensive typed response with more than twenty chars for testing."},
            headers=headers,
        ).json()
        feed_data = client.get(f"/api/v1/interviews/sessions/{int_data['id']}/feedback", headers=headers).json()
        for k in ["rubric_version", "total_score", "dimension_scores", "positive_highlights", "actionable_improvements", "disclaimer"]:
            assert k in feed_data, f"Missing key '{k}' in RubricFeedback schema"

        audit_list = client.get("/api/v1/interviews/audits", headers=headers).json()
        for k in ["total", "audits"]:
            assert k in audit_list, f"Missing key '{k}' in InterviewAuditListResponse schema"
        latest_audit = audit_list["audits"][0]
        for k in ["id", "session_id", "user_id", "model_provider", "evaluated_score", "prompt_injection_flag", "is_fallback", "latency_ms", "created_at"]:
            assert k in latest_audit, f"Missing key '{k}' in InterviewAuditOut schema"

        quality_data = client.get("/api/v1/interviews/audits/quality-report", headers=headers).json()
        for k in ["total_evaluations", "average_score", "prompt_injections_detected", "average_latency_ms", "compliance_rate"]:
            assert k in quality_data, f"Missing key '{k}' in InterviewQualityReport schema"

        # 8. Dashboard contract: DashboardProgressResponse, StreakResponse, ReadinessBreakdown
        dash_data = client.get("/api/v1/progress/dashboard", headers=headers).json()
        for k in [
            "user_id", "target_role", "streak_days", "total_attempts", "correct_attempts",
            "overall_accuracy_percentage", "readiness", "topic_masteries", "activity_timeline", "next_action", "generated_at"
        ]:
            assert k in dash_data, f"Missing key '{k}' in DashboardProgress schema"

        readiness_data = dash_data["readiness"]
        for k in [
            "overall_readiness_score", "profile_resume_score", "practice_mastery_score",
            "job_matching_score", "mock_interview_score", "readiness_level", "disclaimer"
        ]:
            assert k in readiness_data, f"Missing key '{k}' in ReadinessBreakdown schema"
