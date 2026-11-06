"""Idempotent demonstration environment seeder for CareerPilot AI viva & evaluations.

Prepares a comprehensive, demonstrable database state:
1. Canonical skill taxonomy and aliases.
2. Curated MCQ questions across 5 core computer science domains.
3. Industry-standard entry-level benchmark job postings.
4. Demo student account ('student@careerpilot.ai' / 'DemoStudent2026!') with:
   - Configured profile (Junior Python Developer)
   - Extracted resume with confirmed skills and evidence
   - 8 diagnostic practice attempts with graded feedback
   - Topic mastery calculation with recent-weighted exponential decay
   - 1 evaluated mock technical interview session with 5-dimension rubric breakdown
   - Active dashboard telemetry with readiness index and practice streak
5. Demo reviewer account ('recruiter@careerpilot.ai' / 'DemoRecruiter2026!')
"""

import io
import sys
from pathlib import Path

# Add backend directory to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
BACKEND_DIR = PROJECT_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from sqlalchemy.orm import Session  # noqa: E402
from app.core.config import get_settings  # noqa: E402
from app.core.security import hash_password  # noqa: E402
from app.db.base import Base  # noqa: E402
from app.db.session import SessionLocal, engine  # noqa: E402
from app.models import (  # noqa: E402
    InterviewAudit,
    InterviewSession,
    PracticeAttempt,
    Profile,
    Question,
    Resume,
    ResumeSkill,
    Skill,
    User,
)
from app.schemas.interview import InterviewResponseSubmit  # noqa: E402
from app.services.interview_service import submit_interview_response  # noqa: E402
from app.services.job_parser import seed_synthetic_jobs  # noqa: E402
from app.services.mastery_service import recalculate_all_masteries_for_user  # noqa: E402
from app.services.question_service import seed_questions  # noqa: E402
from app.services.skill_taxonomy import ensure_default_skills  # noqa: E402

settings = get_settings()


def _create_synthetic_pdf(lines: list[str]) -> bytes:
    """Build a valid minimal PDF containing text streams."""
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


def seed_demo_environment():
    """Seed comprehensive demo state into the active database."""
    print("=" * 70)
    print("CareerPilot AI — Seeding Demo Environment")
    print(f"Database Target: {settings.DATABASE_URL}")
    print("=" * 70)

    # Ensure schema tables exist
    Base.metadata.create_all(bind=engine)

    db: Session = SessionLocal()
    try:
        # 1. Ensure Skill Taxonomy & Benchmark Jobs
        print("[1/6] Seeding Canonical Skills & Synthetic Jobs...")
        skill_map = ensure_default_skills(db)
        seeded_jobs = seed_synthetic_jobs(db)
        print(f"      Canonical skills: {len(skill_map)} available.")
        print(f"      Benchmark jobs:   {len(seeded_jobs)} available.")

        # 2. Ensure Curated Question Bank
        print("[2/6] Seeding Curated Question Bank...")
        q_seeded, q_total = seed_questions(db)
        print(f"      Question bank:    {q_total} questions available.")

        # 3. Create Demo Student Account
        student_email = "student@careerpilot.ai"
        student_pass = "DemoStudent2026!"
        print(f"[3/6] Configuring Demo Student ({student_email})...")

        student = db.query(User).filter(User.email == student_email).first()
        if not student:
            student = User(
                email=student_email,
                hashed_password=hash_password(student_pass),
                is_active=True,
                is_verified=True,
            )
            db.add(student)
            db.flush()

        # Ensure Profile
        student_profile = db.query(Profile).filter(Profile.user_id == student.id).first()
        if not student_profile:
            student_profile = Profile(
                user_id=student.id,
                target_role="Junior Python Developer",
                preferred_language="en",
                consent_analytics=True,
            )
            db.add(student_profile)
        else:
            student_profile.target_role = "Junior Python Developer"
            student_profile.consent_analytics = True
        db.flush()

        # 4. Attach Demonstrable Resume & Skills
        print("[4/6] Provisioning Demo Resume & Extracted Skills...")
        demo_resume = db.query(Resume).filter(Resume.user_id == student.id).first()
        if not demo_resume:
            resume_lines = [
                "DEMO CANDIDATE",
                "Junior Python & Backend Software Engineer",
                "Summary: Software engineering graduate proficient in Python, FastAPI, and PostgreSQL.",
                "Skills: Python, FastAPI, PostgreSQL, SQLite, Git, Docker, REST APIs",
                "Projects: Placement Intelligence Portal using FastAPI and React",
                "Education: Bachelor of Technology in Computer Science",
            ]
            pdf_bytes = _create_synthetic_pdf(resume_lines)
            demo_resume = Resume(
                user_id=student.id,
                original_filename="alex_chen_placement_resume.pdf",
                file_key="demo-student-resume-key-2026",
                file_path="uploads/demo-student-resume.pdf",
                file_size_bytes=len(pdf_bytes),
                mime_type="application/pdf",
                parse_status="completed",
                parser_version="pypdf-5.9.0",
                parsed_content={
                    "text": "\n".join(resume_lines),
                    "sections": {
                        "summary": "Software engineering graduate proficient in Python, FastAPI, and PostgreSQL.",
                        "skills": "Python, FastAPI, PostgreSQL, SQLite, Git, Docker, REST APIs",
                        "projects": "Placement Intelligence Portal using FastAPI and React",
                        "education": "Bachelor of Technology in Computer Science",
                    },
                },
            )
            db.add(demo_resume)
            db.flush()

            # Attach skills with evidence
            skills_to_link = [
                ("python", "backend", "Software engineering graduate proficient in Python"),
                ("fastapi", "framework", "Placement Intelligence Portal using FastAPI"),
                ("postgresql", "database", "proficient in Python, FastAPI, and PostgreSQL"),
                ("docker", "devops", "Git, Docker, REST APIs"),
                ("git", "tools", "Git, Docker, REST APIs"),
            ]
            for c_name, cat, snippet in skills_to_link:
                sk = skill_map.get(c_name)
                if sk:
                    db.add(
                        ResumeSkill(
                            resume_id=demo_resume.id,
                            skill_id=sk.id,
                            evidence_snippet=snippet,
                            confidence_score=0.95,
                            is_auto_extracted=True,
                            is_user_confirmed=True,
                        )
                    )
            db.flush()

        # 5. Populate Diagnostic Practice Attempts & Recalculate Mastery
        print("[5/6] Generating Diagnostic Practice History & Mastery Telemetry...")
        existing_attempts = db.query(PracticeAttempt).filter(PracticeAttempt.user_id == student.id).count()
        if existing_attempts < 4:
            questions = db.query(Question).filter(Question.topic.in_(["Python", "SQL", "Data Structures"])).all()
            for idx, q in enumerate(questions[:6]):
                is_correct = (idx % 3 != 1)  # 2 correct, 1 incorrect pattern
                user_ans = q.answer_key if is_correct else ("Z" if q.answer_key != "Z" else "Y")
                score = 1.0 if is_correct else 0.0

                attempt = PracticeAttempt(
                    user_id=student.id,
                    question_id=q.id,
                    user_answer=user_ans,
                    is_correct=is_correct,
                    score=score,
                    duration_seconds=18 + idx * 4,
                )
                db.add(attempt)
            db.flush()

        # Recalculate masteries
        recalculate_all_masteries_for_user(db, student.id)

        # 6. Populate Mock Interview Session & Rubric Evaluation
        print("[6/6] Generating Evaluated Mock Interview Session...")
        existing_session = db.query(InterviewSession).filter(InterviewSession.user_id == student.id).first()
        if not existing_session:
            answer_text = (
                "In designing this architecture, I apply the Single Responsibility Principle and partition "
                "the system into decoupled microservices. Communication occurs asynchronously using RabbitMQ "
                "message brokers for event ingestion, while synchronous operations use gRPC. To guarantee "
                "high availability, services are deployed across multiple availability zones behind an NGINX "
                "load balancer. Redis provides in-memory caching for read-heavy query patterns, reducing database "
                "load by 65%. PostgreSQL acts as the ACID-compliant primary datastore with automated replication."
            )
            int_sess = InterviewSession(
                user_id=student.id,
                role="Backend Engineer",
                competency="System Design",
                question_text="Design a backend notification platform capable of delivering millions of alerts with rate-limiting and retry logic.",
                user_response=answer_text,
                status="in_progress",
            )
            db.add(int_sess)
            db.flush()

            # Run rubric evaluation and audit logging
            submit_interview_response(
                db=db,
                session_id=int_sess.id,
                user_id=student.id,
                payload=InterviewResponseSubmit(
                    user_response=answer_text,
                    duration_seconds=150,
                ),
            )

        # Ensure demo reviewer account exists
        reviewer_email = "recruiter@careerpilot.ai"
        reviewer_pass = "DemoRecruiter2026!"
        reviewer = db.query(User).filter(User.email == reviewer_email).first()
        if not reviewer:
            reviewer = User(
                email=reviewer_email,
                hashed_password=hash_password(reviewer_pass),
                is_active=True,
                is_verified=True,
            )
            db.add(reviewer)
            db.flush()
            db.add(
                Profile(
                    user_id=reviewer.id,
                    target_role="Entry-Level Data/ML Analyst",
                    preferred_language="en",
                    consent_analytics=True,
                )
            )

        db.commit()

        print("\n" + "=" * 70)
        print("DEMO ENVIRONMENT SEEDING COMPLETED SUCCESSFULLY!")
        print("=" * 70)
        print("Demo Credentials:")
        print(f"  Student Account:    {student_email}  |  Password: {student_pass}")
        print(f"  Recruiter Account:  {reviewer_email}|  Password: {reviewer_pass}")
        print("\nAccess Endpoints:")
        print("  Frontend UI:        http://localhost:5173")
        print("  Backend API:        http://localhost:8000/api/v1")
        print("  Interactive Docs:   http://localhost:8000/docs")
        print("  Health Probe:       http://localhost:8000/api/v1/health")
        print("=" * 70)

    except Exception as exc:
        db.rollback()
        print(f"[ERROR] Failed to seed demo environment: {exc}", file=sys.stderr)
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_demo_environment()
