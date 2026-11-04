"""Service layer for grading practice attempts, recording results, and computing statistics."""

from typing import Any, Dict, List, Optional, Tuple
from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.models import PracticeAttempt, PracticeSession, Question
from app.schemas.practice_attempt import (
    AttemptFeedback,
    AttemptHistoryItem,
    AttemptStatsSummary,
    AttemptSubmit,
    TopicStat,
)


def grade_and_record_attempt(
    db: Session,
    user_id: int,
    submit_in: AttemptSubmit,
) -> Tuple[PracticeAttempt, Question]:
    """Deterministically grade a user's answer and record the attempt in persistence.

    Args:
        db: SQLAlchemy database session.
        user_id: ID of the authenticated user submitting the attempt.
        submit_in: The attempt payload containing question_id, user_answer, and optional session_id.

    Returns:
        Tuple of (PracticeAttempt, Question).

    Raises:
        ValueError: If question does not exist, is inactive, or session validation fails.
    """
    question = db.get(Question, submit_in.question_id)
    if not question or not question.is_active:
        raise ValueError(f"Question with ID {submit_in.question_id} not found or inactive.")

    practice_session: Optional[PracticeSession] = None
    if submit_in.session_id:
        practice_session = db.scalar(
            select(PracticeSession).where(
                PracticeSession.session_id == submit_in.session_id,
                PracticeSession.user_id == user_id,
            )
        )
        if not practice_session:
            raise ValueError(f"Practice session '{submit_in.session_id}' not found or access denied.")
        if practice_session.status != "in_progress":
            raise ValueError(f"Practice session is already {practice_session.status}.")

    # Deterministic grading
    clean_user_answer = submit_in.user_answer.strip().upper()
    clean_answer_key = question.answer_key.strip().upper()
    is_correct = clean_user_answer == clean_answer_key
    score = 1.0 if is_correct else 0.0

    attempt = PracticeAttempt(
        user_id=user_id,
        question_id=question.id,
        session_id=submit_in.session_id,
        user_answer=clean_user_answer,
        is_correct=is_correct,
        score=score,
        duration_seconds=submit_in.duration_seconds,
        grading_version=question.rubric_version or "1.0.0",
    )
    db.add(attempt)
    db.flush()  # Flush so attempt is visible to queries in the same transaction

    # Update session score if linked to a practice session
    if practice_session:
        session_attempts = db.scalars(
            select(PracticeAttempt).where(PracticeAttempt.session_id == practice_session.session_id)
        ).all()
        correct_count = sum(1 for a in session_attempts if a.is_correct)
        if practice_session.total_questions > 0:
            practice_session.score = round(
                (correct_count / practice_session.total_questions) * 100.0, 1
            )

    db.commit()
    db.refresh(attempt)
    return attempt, question


def get_user_attempts(
    db: Session,
    user_id: int,
    topic: Optional[str] = None,
    session_id: Optional[str] = None,
    is_correct: Optional[bool] = None,
    skip: int = 0,
    limit: int = 50,
) -> Tuple[List[AttemptHistoryItem], int]:
    """Retrieve historical practice attempts for a user with question context."""
    query = (
        select(PracticeAttempt, Question)
        .join(Question, PracticeAttempt.question_id == Question.id)
        .where(PracticeAttempt.user_id == user_id)
    )
    count_query = (
        select(func.count(PracticeAttempt.id))
        .join(Question, PracticeAttempt.question_id == Question.id)
        .where(PracticeAttempt.user_id == user_id)
    )

    if topic:
        query = query.where(Question.topic == topic.strip())
        count_query = count_query.where(Question.topic == topic.strip())

    if session_id:
        query = query.where(PracticeAttempt.session_id == session_id.strip())
        count_query = count_query.where(PracticeAttempt.session_id == session_id.strip())

    if is_correct is not None:
        query = query.where(PracticeAttempt.is_correct == is_correct)
        count_query = count_query.where(PracticeAttempt.is_correct == is_correct)

    total = db.scalar(count_query) or 0
    rows = db.execute(
        query.order_by(PracticeAttempt.created_at.desc()).offset(skip).limit(limit)
    ).all()

    items = [
        AttemptHistoryItem(
            id=att.id,
            question_id=att.question_id,
            session_id=att.session_id,
            topic=q.topic,
            difficulty=q.difficulty,
            prompt=q.prompt,
            user_answer=att.user_answer,
            correct_answer_key=q.answer_key,
            is_correct=att.is_correct,
            score=att.score,
            duration_seconds=att.duration_seconds,
            created_at=att.created_at,
        )
        for att, q in rows
    ]

    return items, total


def get_user_attempt_stats(db: Session, user_id: int) -> AttemptStatsSummary:
    """Compute aggregate accuracy, count, and duration statistics for a user."""
    rows = db.execute(
        select(
            PracticeAttempt.is_correct,
            PracticeAttempt.duration_seconds,
            Question.topic,
            Question.difficulty,
        )
        .join(Question, PracticeAttempt.question_id == Question.id)
        .where(PracticeAttempt.user_id == user_id)
    ).all()

    total_attempts = len(rows)
    if total_attempts == 0:
        return AttemptStatsSummary(
            total_attempts=0,
            correct_attempts=0,
            accuracy_percentage=0.0,
            total_time_seconds=0,
            by_topic={},
            by_difficulty={},
        )

    correct_count = sum(1 for r in rows if r[0])
    total_time = sum(r[1] or 0 for r in rows)
    accuracy_pct = round((correct_count / total_attempts) * 100.0, 1)

    # Breakdown by topic
    topic_data: Dict[str, Dict[str, int]] = {}
    difficulty_data: Dict[str, Dict[str, int]] = {}

    for is_corr, _, topic, difficulty in rows:
        # Topic grouping
        if topic not in topic_data:
            topic_data[topic] = {"total": 0, "correct": 0}
        topic_data[topic]["total"] += 1
        if is_corr:
            topic_data[topic]["correct"] += 1

        # Difficulty grouping
        diff_key = difficulty.lower() if difficulty else "medium"
        if diff_key not in difficulty_data:
            difficulty_data[diff_key] = {"total": 0, "correct": 0}
        difficulty_data[diff_key]["total"] += 1
        if is_corr:
            difficulty_data[diff_key]["correct"] += 1

    by_topic = {
        top: TopicStat(
            total_attempts=val["total"],
            correct_attempts=val["correct"],
            accuracy_percentage=round((val["correct"] / val["total"]) * 100.0, 1)
            if val["total"] > 0
            else 0.0,
        )
        for top, val in sorted(topic_data.items(), key=lambda x: x[0])
    }

    by_diff = {
        diff: TopicStat(
            total_attempts=val["total"],
            correct_attempts=val["correct"],
            accuracy_percentage=round((val["correct"] / val["total"]) * 100.0, 1)
            if val["total"] > 0
            else 0.0,
        )
        for diff, val in sorted(difficulty_data.items(), key=lambda x: x[0])
    }

    return AttemptStatsSummary(
        total_attempts=total_attempts,
        correct_attempts=correct_count,
        accuracy_percentage=accuracy_pct,
        total_time_seconds=total_time,
        by_topic=by_topic,
        by_difficulty=by_diff,
    )
