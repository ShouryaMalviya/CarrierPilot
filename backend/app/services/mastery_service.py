"""Transparent topic mastery estimation service implementing recent-weighted exponential decay heuristic."""

from datetime import datetime, timezone
import math
from typing import Any, Dict, List, Optional, Tuple
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import PracticeAttempt, Question, TopicMastery
from app.schemas.topic_mastery import (
    AttemptWeightContribution,
    MasteryCalculationExplanation,
)

DECAY_GAMMA: float = 0.85
MAX_ATTEMPT_WINDOW: int = 20

DIFFICULTY_FACTORS: Dict[str, float] = {
    "easy": 0.8,
    "medium": 1.0,
    "hard": 1.2,
}


def get_difficulty_factor(difficulty: Optional[str]) -> float:
    """Return difficulty weighting factor (0.8 for easy, 1.0 for medium, 1.2 for hard)."""
    if not difficulty:
        return 1.0
    return DIFFICULTY_FACTORS.get(difficulty.strip().lower(), 1.0)


def calculate_topic_mastery(
    attempts: List[Tuple[PracticeAttempt, Question]],
    decay: float = DECAY_GAMMA,
) -> Tuple[float, List[str], float, float, List[Dict[str, Any]]]:
    """Calculate deterministic recent-weighted mastery score and reason codes.

    Formula:
        Mastery = (sum_{i=1}^N w_i * c_i * d_i) / (sum_{i=1}^N w_i * d_i) * 100
        where:
            w_i = decay^(N - i)  (i=N is most recent attempt, weight = 1.0)
            c_i in {0.0, 1.0}    (1.0 if attempt.is_correct else 0.0)
            d_i in {0.8, 1.0, 1.2} according to difficulty tier

    Returns:
        (mastery_score, reason_codes, numerator_sum, denominator_sum, contributions)
    """
    if not attempts:
        return 0.0, ["NO_DATA"], 0.0, 0.0, []

    # Constrain to recent window (chronological order)
    window = attempts[-MAX_ATTEMPT_WINDOW:]
    n = len(window)

    numerator = 0.0
    denominator = 0.0
    contributions: List[Dict[str, Any]] = []

    for i, (att, q) in enumerate(window, start=1):
        # Recency index: 0 for most recent (i=n), n-1 for oldest (i=1)
        recency_idx = n - i
        weight = round(math.pow(decay, recency_idx), 4)
        diff_factor = get_difficulty_factor(q.difficulty)
        correctness = 1.0 if att.is_correct else 0.0

        weighted_score = round(weight * correctness * diff_factor, 4)
        max_possible = round(weight * 1.0 * diff_factor, 4)

        numerator += weighted_score
        denominator += max_possible

        contributions.append({
            "attempt_id": att.id,
            "question_id": q.id,
            "difficulty": q.difficulty,
            "is_correct": att.is_correct,
            "recency_index": recency_idx,
            "weight": weight,
            "difficulty_factor": diff_factor,
            "weighted_score": weighted_score,
            "max_possible_weighted_score": max_possible,
        })

    raw_score = (numerator / denominator) * 100.0 if denominator > 0.0 else 0.0
    mastery_score = round(max(0.0, min(100.0, raw_score)), 1)

    # Derive transparent reason codes
    reason_codes: List[str] = []
    if n < 3:
        reason_codes.append("FEW_ATTEMPTS")
    if mastery_score >= 80.0:
        reason_codes.append("HIGH_ACCURACY")
    if mastery_score >= 75.0 and n >= 3:
        reason_codes.append("TOPIC_PROFICIENT")
    if mastery_score < 60.0:
        reason_codes.append("NEEDS_PRACTICE")

    # Check for recent medium/hard struggle (in last 3 attempts)
    recent_hard_attempts = [
        (att, q)
        for att, q in window[-3:]
        if (q.difficulty or "").lower() in ("medium", "hard")
    ]
    if recent_hard_attempts and any(not att.is_correct for att, _ in recent_hard_attempts):
        reason_codes.append("STRUGGLING_MEDIUM_HARD")

    # Check for recent improvement (first half vs second half)
    if n >= 4:
        half = n // 2
        acc_first = sum(1 for a, _ in window[:half] if a.is_correct) / half
        acc_second = sum(1 for a, _ in window[half:] if a.is_correct) / (n - half)
        if acc_second >= acc_first + 0.20:
            reason_codes.append("RECENT_IMPROVEMENT")

    return (
        mastery_score,
        reason_codes,
        round(numerator, 4),
        round(denominator, 4),
        contributions,
    )


def update_user_topic_mastery(
    db: Session,
    user_id: int,
    topic: str,
) -> TopicMastery:
    """Recalculate and persist mastery estimate for a user on a given topic."""
    rows = db.execute(
        select(PracticeAttempt, Question)
        .join(Question, PracticeAttempt.question_id == Question.id)
        .where(
            PracticeAttempt.user_id == user_id,
            Question.topic == topic.strip(),
        )
        .order_by(PracticeAttempt.created_at.asc())
    ).all()

    attempts = [(row[0], row[1]) for row in rows]
    score, reasons, _, _, _ = calculate_topic_mastery(attempts)

    record = db.scalar(
        select(TopicMastery).where(
            TopicMastery.user_id == user_id,
            TopicMastery.topic == topic.strip(),
        )
    )

    if record is None:
        record = TopicMastery(
            user_id=user_id,
            topic=topic.strip(),
            mastery_score=score,
            recent_attempts_count=len(attempts),
            reason_codes=reasons,
        )
        db.add(record)
    else:
        record.mastery_score = score
        record.recent_attempts_count = len(attempts)
        record.reason_codes = reasons
        record.last_calculated_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(record)
    return record


def get_all_distinct_topics(db: Session) -> List[str]:
    """Retrieve all available topic names from the question bank."""
    topics = db.scalars(
        select(Question.topic).where(Question.is_active.is_(True)).distinct()
    ).all()
    return sorted(list({t.strip() for t in topics if t and t.strip()}))


def recalculate_all_masteries_for_user(
    db: Session,
    user_id: int,
) -> List[TopicMastery]:
    """Recalculate mastery across all known topics for a user."""
    topics = get_all_distinct_topics(db)
    if not topics:
        topics = ["Python", "Data Structures", "SQL", "Web Development", "DevOps"]

    records: List[TopicMastery] = []
    for t in topics:
        rec = update_user_topic_mastery(db, user_id, t)
        records.append(rec)
    return records


def get_user_topic_masteries(
    db: Session,
    user_id: int,
) -> List[TopicMastery]:
    """Retrieve topic mastery records for a user, initializing any missing topics."""
    records = list(
        db.scalars(
            select(TopicMastery)
            .where(TopicMastery.user_id == user_id)
            .order_by(TopicMastery.topic.asc())
        ).all()
    )

    all_topics = get_all_distinct_topics(db)
    existing_topics = {r.topic for r in records}

    missing_topics = [t for t in all_topics if t not in existing_topics]
    if missing_topics:
        for t in missing_topics:
            rec = update_user_topic_mastery(db, user_id, t)
            records.append(rec)
        records.sort(key=lambda x: x.topic)

    return records


def explain_topic_mastery(
    db: Session,
    user_id: int,
    topic: str,
) -> MasteryCalculationExplanation:
    """Generate detailed audit trail and step-by-step math for a topic mastery score."""
    rows = db.execute(
        select(PracticeAttempt, Question)
        .join(Question, PracticeAttempt.question_id == Question.id)
        .where(
            PracticeAttempt.user_id == user_id,
            Question.topic == topic.strip(),
        )
        .order_by(PracticeAttempt.created_at.asc())
    ).all()

    attempts = [(row[0], row[1]) for row in rows]
    score, reasons, num_sum, den_sum, contrib_dicts = calculate_topic_mastery(attempts)

    contributions = [AttemptWeightContribution(**c) for c in contrib_dicts]

    return MasteryCalculationExplanation(
        topic=topic.strip(),
        mastery_score=score,
        total_attempts=len(attempts),
        decay_gamma=DECAY_GAMMA,
        numerator_sum=num_sum,
        denominator_sum=den_sum,
        reason_codes=reasons,
        attempt_contributions=contributions,
        last_calculated_at=datetime.now(timezone.utc),
    )

