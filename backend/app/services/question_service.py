"""Question bank service managing curated practice questions and topic taxonomy."""

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Question
from app.schemas.question import (
    QuestionCreate,
    QuestionOption,
    QuestionUpdate,
    TopicSummary,
)

logger = logging.getLogger(__name__)

SEED_QUESTIONS_PATH = Path(__file__).resolve().parent.parent / "data" / "seed_questions.json"


def load_seed_questions_data() -> List[Dict[str, Any]]:
    """Load curated seed questions from static JSON fixture."""
    if not SEED_QUESTIONS_PATH.exists():
        logger.warning("Seed questions file not found at %s", SEED_QUESTIONS_PATH)
        return []
    with open(SEED_QUESTIONS_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def seed_questions(db: Session, force_reset: bool = False) -> Tuple[int, int]:
    """Seed curated technical questions into the database idempotently.

    Args:
        db: SQLAlchemy database session.
        force_reset: If True, delete all existing synthetic questions before seeding.

    Returns:
        Tuple of (newly_seeded_count, total_questions_count).
    """
    raw_data = load_seed_questions_data()
    if not raw_data:
        return 0, db.scalar(select(func.count(Question.id))) or 0

    if force_reset:
        db.query(Question).filter(Question.is_synthetic.is_(True)).delete(synchronize_session=False)
        db.commit()

    existing_prompts = {
        row[0] for row in db.execute(select(Question.prompt)).all()
    }

    new_questions: List[Question] = []
    for item in raw_data:
        prompt = item.get("prompt", "").strip()
        if prompt in existing_prompts:
            continue

        q = Question(
            topic=item["topic"].strip(),
            difficulty=item.get("difficulty", "medium").strip().lower(),
            question_type=item.get("question_type", "mcq").strip().lower(),
            prompt=prompt,
            options=item.get("options", []),
            answer_key=item["answer_key"].strip().upper(),
            explanation=item.get("explanation", "").strip(),
            rubric_version=item.get("rubric_version", "1.0.0"),
            is_active=item.get("is_active", True),
            is_synthetic=item.get("is_synthetic", True),
        )
        new_questions.append(q)
        existing_prompts.add(prompt)

    if new_questions:
        db.add_all(new_questions)
        db.commit()

    total_count = db.scalar(select(func.count(Question.id))) or 0
    return len(new_questions), total_count


def get_question(db: Session, question_id: int) -> Optional[Question]:
    """Retrieve a single question by primary key."""
    return db.get(Question, question_id)


def list_questions(
    db: Session,
    topic: Optional[str] = None,
    difficulty: Optional[str] = None,
    is_active: Optional[bool] = True,
    skip: int = 0,
    limit: int = 50,
) -> Tuple[List[Question], int]:
    """Query questions with optional filtering by topic and difficulty."""
    query = select(Question)
    count_query = select(func.count(Question.id))

    if topic:
        query = query.where(Question.topic == topic.strip())
        count_query = count_query.where(Question.topic == topic.strip())

    if difficulty:
        query = query.where(Question.difficulty == difficulty.strip().lower())
        count_query = count_query.where(Question.difficulty == difficulty.strip().lower())

    if is_active is not None:
        query = query.where(Question.is_active == is_active)
        count_query = count_query.where(Question.is_active == is_active)

    total = db.scalar(count_query) or 0
    questions = db.execute(
        query.order_by(Question.id.asc()).offset(skip).limit(limit)
    ).scalars().all()

    return list(questions), total


def get_topic_summaries(db: Session) -> List[TopicSummary]:
    """Aggregate questions by topic domain and difficulty level."""
    rows = db.execute(
        select(
            Question.topic,
            Question.difficulty,
            func.count(Question.id),
        )
        .where(Question.is_active.is_(True))
        .group_by(Question.topic, Question.difficulty)
    ).all()

    topic_dict: Dict[str, Dict[str, int]] = {}
    for topic, difficulty, count in rows:
        if topic not in topic_dict:
            topic_dict[topic] = {"total": 0, "easy": 0, "medium": 0, "hard": 0}
        diff_key = difficulty.lower() if difficulty.lower() in ("easy", "medium", "hard") else "medium"
        topic_dict[topic][diff_key] += count
        topic_dict[topic]["total"] += count

    summaries = [
        TopicSummary(
            topic=t,
            total_questions=data["total"],
            easy_count=data["easy"],
            medium_count=data["medium"],
            hard_count=data["hard"],
        )
        for t, data in sorted(topic_dict.items(), key=lambda x: x[0])
    ]
    return summaries


def create_question(db: Session, question_in: QuestionCreate) -> Question:
    """Create and persist a new practice question."""
    q = Question(
        topic=question_in.topic.strip(),
        difficulty=question_in.difficulty,
        question_type=question_in.question_type,
        prompt=question_in.prompt.strip(),
        options=[opt.model_dump() for opt in question_in.options],
        answer_key=question_in.answer_key.strip().upper(),
        explanation=question_in.explanation.strip(),
        rubric_version=question_in.rubric_version,
        is_active=question_in.is_active,
        is_synthetic=question_in.is_synthetic,
    )
    db.add(q)
    db.commit()
    db.refresh(q)
    return q


def update_question(db: Session, question: Question, question_in: QuestionUpdate) -> Question:
    """Update fields on an existing question."""
    update_data = question_in.model_dump(exclude_unset=True)
    if "options" in update_data and update_data["options"] is not None:
        update_data["options"] = [opt.model_dump() if hasattr(opt, "model_dump") else opt for opt in question_in.options]  # type: ignore

    for field, value in update_data.items():
        if value is not None:
            setattr(question, field, value)

    db.commit()
    db.refresh(question)
    return question


def delete_question(db: Session, question: Question) -> None:
    """Delete a question from the database."""
    db.delete(question)
    db.commit()

