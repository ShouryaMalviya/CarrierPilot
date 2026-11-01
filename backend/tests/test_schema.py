"""Database schema and relational constraint tests for CareerPilot AI."""

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.models import (
    InterviewSession,
    Job,
    JobSkill,
    PracticeAttempt,
    Profile,
    Question,
    RecommendationAudit,
    Resume,
    ResumeSkill,
    Skill,
    TopicMastery,
    User,
)


@event.listens_for(Engine, "connect")
def _set_sqlite_pragma(dbapi_connection, connection_record):
    """Enforce foreign key constraints in SQLite test engine."""
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


@pytest.fixture
def db_session():
    """Create a pristine in-memory SQLite database for schema testing."""
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(bind=engine)
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)
    session = session_factory()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


def test_user_and_profile_creation(db_session):
    """Verify user and associated profile creation with relationship linking."""
    user = User(
        email="student@example.com",
        hashed_password="hashed_pw_placeholder",
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()

    profile = Profile(
        user_id=user.id,
        target_role="Junior Python Developer",
        preferred_language="English",
    )
    db_session.add(profile)
    db_session.commit()

    assert user.id is not None
    assert user.profile is not None
    assert user.profile.target_role == "Junior Python Developer"
    assert profile.user.email == "student@example.com"


def test_duplicate_user_email_rejected(db_session):
    """Verify unique constraint on user email."""
    user1 = User(email="duplicate@example.com", hashed_password="pw1")
    user2 = User(email="duplicate@example.com", hashed_password="pw2")
    db_session.add(user1)
    db_session.commit()

    db_session.add(user2)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_duplicate_skill_canonical_name_rejected(db_session):
    """Verify unique constraint on canonical skill name."""
    skill1 = Skill(canonical_name="Python", category="languages")
    skill2 = Skill(canonical_name="Python", category="languages")
    db_session.add(skill1)
    db_session.commit()

    db_session.add(skill2)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_resume_and_skills_evidence_workflow(db_session):
    """Verify resume creation, skill linking, evidence storage, and uniqueness."""
    user = User(email="candidate@example.com", hashed_password="pw")
    db_session.add(user)
    db_session.commit()

    resume = Resume(
        user_id=user.id,
        original_filename="resume.pdf",
        file_key="uuid-opaque-12345",
        file_path="/safe/storage/uuid-opaque-12345.pdf",
        file_size_bytes=1048576,
        mime_type="application/pdf",
        parse_status="completed",
    )
    skill = Skill(canonical_name="FastAPI", category="frameworks", aliases=["Fast API"])
    db_session.add_all([resume, skill])
    db_session.commit()

    resume_skill = ResumeSkill(
        resume_id=resume.id,
        skill_id=skill.id,
        evidence_snippet="Built microservices using FastAPI and Docker",
        confidence_score=0.95,
        is_user_confirmed=False,
        is_auto_extracted=True,
    )
    db_session.add(resume_skill)
    db_session.commit()

    assert len(resume.resume_skills) == 1
    assert resume.resume_skills[0].evidence_snippet.startswith("Built microservices")

    # Duplicate (resume_id, skill_id) should fail
    duplicate_link = ResumeSkill(resume_id=resume.id, skill_id=skill.id)
    db_session.add(duplicate_link)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_foreign_key_enforcement(db_session):
    """Verify that foreign key constraints prevent orphan records."""
    invalid_profile = Profile(user_id=99999, target_role="Data Analyst")
    db_session.add(invalid_profile)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_cascade_delete_user(db_session):
    """Verify that deleting a user cascades to delete their profile, resumes, and attempts."""
    user = User(email="delete_me@example.com", hashed_password="pw")
    db_session.add(user)
    db_session.commit()

    profile = Profile(user_id=user.id)
    resume = Resume(
        user_id=user.id,
        original_filename="temp.pdf",
        file_key="uuid-del-123",
        file_path="/safe/del.pdf",
        file_size_bytes=1000,
        mime_type="application/pdf",
    )
    skill = Skill(canonical_name="SQL", category="databases")
    question = Question(
        topic="SQL",
        difficulty="easy",
        question_type="mcq",
        prompt="What is SELECT?",
        answer_key="Queries data",
        explanation="Basic query keyword",
    )
    db_session.add_all([profile, resume, skill, question])
    db_session.commit()

    attempt = PracticeAttempt(
        user_id=user.id,
        question_id=question.id,
        user_answer="Queries data",
        is_correct=True,
        score=100.0,
    )
    session_rec = InterviewSession(
        user_id=user.id,
        role="Junior Python Developer",
        competency="Algorithms",
        question_text="Explain quicksort",
    )
    mastery = TopicMastery(
        user_id=user.id,
        topic="SQL",
        mastery_score=85.0,
    )
    audit = RecommendationAudit(
        user_id=user.id,
        recommendation_type="next_question",
        rationale="Topic needs review",
        reason_code="RECENT_LOW_SCORE",
    )
    db_session.add_all([attempt, session_rec, mastery, audit])
    db_session.commit()

    # Now delete the user
    db_session.delete(user)
    db_session.commit()

    # Verify cascades
    assert db_session.query(Profile).filter_by(user_id=user.id).first() is None
    assert db_session.query(Resume).filter_by(user_id=user.id).first() is None
    assert db_session.query(PracticeAttempt).filter_by(user_id=user.id).first() is None
    assert db_session.query(InterviewSession).filter_by(user_id=user.id).first() is None
    assert db_session.query(TopicMastery).filter_by(user_id=user.id).first() is None
    assert db_session.query(RecommendationAudit).filter_by(user_id=user.id).first() is None

    # Global skill and question must NOT be deleted
    assert db_session.query(Skill).filter_by(canonical_name="SQL").first() is not None
    assert db_session.query(Question).filter_by(topic="SQL").first() is not None

