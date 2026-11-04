"""Adaptive rule-based practice recommender and structured study plan engine."""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set, Tuple
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import PracticeAttempt, Profile, Question, RecommendationAudit, TopicMastery
from app.schemas.question import QuestionPublic
from app.schemas.recommendation import (
    NextQuestionRecommendation,
    StudyPlanResponse,
    StudyPlanTopicItem,
)
from app.services import mastery_service
from app.services.question_service import seed_questions

# Mapping target roles to prioritized curriculum topics
ROLE_CURRICULUM_PRIORITY: Dict[str, List[str]] = {
    "Junior Python Developer": ["Python", "SQL", "Data Structures", "DevOps", "Web Development"],
    "Entry-Level Data/ML Analyst": ["SQL", "Python", "Data Structures", "DevOps", "Web Development"],
    "Associate Frontend Developer": ["Web Development", "Data Structures", "Python", "SQL", "DevOps"],
}

DEFAULT_CURRICULUM: List[str] = [
    "Python",
    "Data Structures",
    "SQL",
    "Web Development",
    "DevOps",
]


def get_user_target_role(db: Session, user_id: int) -> str:
    """Retrieve user's target role from profile or default to Junior Python Developer."""
    role = db.scalar(select(Profile.target_role).where(Profile.user_id == user_id))
    if role and role.strip():
        return role.strip()
    return "Junior Python Developer"


def get_ordered_curriculum_for_role(target_role: str) -> List[str]:
    """Return ordered topic domain sequence tailored to target role."""
    return ROLE_CURRICULUM_PRIORITY.get(target_role, DEFAULT_CURRICULUM)


def log_recommendation_audit(
    db: Session,
    user_id: int,
    recommendation_type: str,
    target_id: Optional[str],
    rationale: str,
    reason_code: str,
) -> RecommendationAudit:
    """Persist recommendation rationale and decision code into audit trail."""
    audit = RecommendationAudit(
        user_id=user_id,
        recommendation_type=recommendation_type,
        target_id=str(target_id) if target_id is not None else None,
        rationale=rationale,
        reason_code=reason_code,
    )
    db.add(audit)
    db.commit()
    db.refresh(audit)
    return audit


def select_next_question(
    db: Session,
    user_id: int,
) -> NextQuestionRecommendation:
    """Select the next recommended practice question using transparent rule-based prioritization.

    Hierarchy:
    1. Unpracticed core topics in target role (recent_attempts == 0) -> UNPRACTICED_CORE_DOMAIN (High Priority)
    2. Weak topics with mastery < 60% -> WEAK_TOPIC_REMEDIATION (High Priority)
    3. Intermediate topics with 60% <= mastery < 75% -> CHALLENGE_ADVANCEMENT (Medium Priority)
    4. Retention refresh on proficient topics -> RETENTION_REFRESH (Low Priority)
    """
    # Ensure question bank is seeded
    total_q = db.scalar(select(func.count(Question.id))) or 0
    if total_q == 0:
        seed_questions(db)

    target_role = get_user_target_role(db, user_id)
    ordered_topics = get_ordered_curriculum_for_role(target_role)

    # Get user topic masteries (guaranteed complete across all distinct topics)
    masteries = mastery_service.get_user_topic_masteries(db, user_id)
    mastery_dict = {m.topic: m for m in masteries}

    # Fetch IDs of questions the user has attempted
    attempted_qids: Set[int] = set(
        db.scalars(select(PracticeAttempt.question_id).where(PracticeAttempt.user_id == user_id)).all()
    )

    # Fetch IDs of questions the user got wrong
    incorrect_qids: Set[int] = set(
        db.scalars(
            select(PracticeAttempt.question_id).where(
                PracticeAttempt.user_id == user_id,
                PracticeAttempt.is_correct.is_(False),
            )
        ).all()
    )

    selected_question: Optional[Question] = None
    reason_code = "GENERAL_PRACTICE"
    rationale = "Recommended for general technical skill consolidation."
    priority_level = "medium"
    topic_mastery_score = 0.0

    # --------------------------------------------------------------------------
    # Rule 1: Weak Topic Remediation (mastery < 60% with attempts > 0)
    # --------------------------------------------------------------------------
    weak_topics = [
        m for m in masteries
        if m.recent_attempts_count > 0 and m.mastery_score < 60.0
    ]
    # Sort by lowest mastery score first
    weak_topics.sort(key=lambda x: x.mastery_score)

    for weak in weak_topics:
        # First preference: an unattempted question in this weak topic
        unattempted = db.scalar(
            select(Question)
            .where(
                Question.topic == weak.topic,
                Question.is_active.is_(True),
                Question.id.not_in(attempted_qids) if attempted_qids else True,
            )
            .order_by(Question.difficulty.asc(), Question.id.asc())
        )
        if unattempted:
            selected_question = unattempted
        else:
            # Second preference: a question previously answered incorrectly in this topic
            retry_q = db.scalar(
                select(Question)
                .where(
                    Question.topic == weak.topic,
                    Question.is_active.is_(True),
                    Question.id.in_(incorrect_qids) if incorrect_qids else True,
                )
                .order_by(Question.id.asc())
            )
            if retry_q:
                selected_question = retry_q

        if selected_question:
            reason_code = "WEAK_TOPIC_REMEDIATION"
            rationale = (
                f"Recommended to remediate your performance in '{weak.topic}', where your "
                f"current estimated mastery is {weak.mastery_score:.1f}% (below the 60% proficiency threshold)."
            )
            priority_level = "high"
            topic_mastery_score = weak.mastery_score
            break

    # --------------------------------------------------------------------------
    # Rule 2: Unpracticed Core Topics in User's Target Role
    # --------------------------------------------------------------------------
    if not selected_question:
        for topic in ordered_topics:
            m = mastery_dict.get(topic)
            if m and m.recent_attempts_count == 0:
                # Look for an easy or medium question in this unpracticed topic
                candidate = db.scalar(
                    select(Question)
                    .where(
                        Question.topic == topic,
                        Question.is_active.is_(True),
                        Question.difficulty.in_(["easy", "medium"]),
                    )
                    .order_by(Question.difficulty.asc(), Question.id.asc())
                )
                if candidate:
                    selected_question = candidate
                    reason_code = "UNPRACTICED_CORE_DOMAIN"
                    rationale = (
                        f"You have not completed any practice in '{topic}', which is a core "
                        f"foundational requirement for your target role of {target_role}."
                    )
                    priority_level = "high"
                    topic_mastery_score = 0.0
                    break

    # --------------------------------------------------------------------------
    # Rule 3: Intermediate Consolidation (60% <= mastery < 75%)
    # --------------------------------------------------------------------------
    if not selected_question:
        intermediate_topics = [
            m for m in masteries
            if 60.0 <= m.mastery_score < 75.0
        ]
        intermediate_topics.sort(key=lambda x: x.mastery_score)

        for inter in intermediate_topics:
            candidate = db.scalar(
                select(Question)
                .where(
                    Question.topic == inter.topic,
                    Question.is_active.is_(True),
                    Question.difficulty.in_(["medium", "hard"]),
                    Question.id.not_in(attempted_qids) if attempted_qids else True,
                )
                .order_by(Question.difficulty.desc(), Question.id.asc())
            )
            if candidate:
                selected_question = candidate
                reason_code = "CHALLENGE_ADVANCEMENT"
                rationale = (
                    f"Recommended to advance your mastery in '{inter.topic}' from intermediate "
                    f"({inter.mastery_score:.1f}%) toward the 75%+ proficient tier."
                )
                priority_level = "medium"
                topic_mastery_score = inter.mastery_score
                break

    # --------------------------------------------------------------------------
    # Rule 4: Retention Refresh (mastery >= 75%)
    # --------------------------------------------------------------------------
    if not selected_question:
        proficient_topics = [m for m in masteries if m.mastery_score >= 75.0]
        if proficient_topics:
            # Pick least recently calculated or practiced topic
            proficient_topics.sort(key=lambda x: x.last_calculated_at)
            top = proficient_topics[0]
            candidate = db.scalar(
                select(Question)
                .where(
                    Question.topic == top.topic,
                    Question.is_active.is_(True),
                )
                .order_by(Question.difficulty.desc(), Question.id.asc())
            )
            if candidate:
                selected_question = candidate
                reason_code = "RETENTION_REFRESH"
                rationale = (
                    f"Recommended as a retention challenge in '{top.topic}' (current mastery: "
                    f"{top.mastery_score:.1f}%) to consolidate long-term placement readiness."
                )
                priority_level = "low"
                topic_mastery_score = top.mastery_score

    # --------------------------------------------------------------------------
    # Ultimate Fallback: Any active question in the bank
    # --------------------------------------------------------------------------
    if not selected_question:
        selected_question = db.scalar(
            select(Question).where(Question.is_active.is_(True)).order_by(Question.id.asc())
        )
        if selected_question:
            m = mastery_dict.get(selected_question.topic)
            topic_mastery_score = m.mastery_score if m else 0.0

    if not selected_question:
        raise ValueError("No active questions available in the question bank.")

    # Record decision audit trail
    log_recommendation_audit(
        db=db,
        user_id=user_id,
        recommendation_type="next_question",
        target_id=str(selected_question.id),
        rationale=rationale,
        reason_code=reason_code,
    )

    public_q = QuestionPublic.model_validate(selected_question)
    return NextQuestionRecommendation(
        question=public_q,
        reason_code=reason_code,
        rationale=rationale,
        priority_level=priority_level,  # type: ignore
        topic_mastery_score=topic_mastery_score,
        target_role=target_role,
    )


def generate_study_plan(
    db: Session,
    user_id: int,
) -> StudyPlanResponse:
    """Generate a structured, prioritized diagnostic study roadmap for the user."""
    target_role = get_user_target_role(db, user_id)
    ordered_curriculum = get_ordered_curriculum_for_role(target_role)

    masteries = mastery_service.get_user_topic_masteries(db, user_id)
    mastery_dict = {m.topic: m for m in masteries}

    # Order topics by role priority, then any remaining topics
    sorted_topics: List[str] = []
    for t in ordered_curriculum:
        if t in mastery_dict and t not in sorted_topics:
            sorted_topics.append(t)
    for t in mastery_dict:
        if t not in sorted_topics:
            sorted_topics.append(t)

    plan_items: List[StudyPlanTopicItem] = []
    for topic_name in sorted_topics:
        m = mastery_dict[topic_name]
        score = m.mastery_score
        attempts = m.recent_attempts_count

        if attempts == 0 or score < 60.0:
            priority_tier = "immediate_remediation"
            rec_count = 5
            suggested_diff = "easy" if score < 30.0 else "medium"
            reason_code = "UNPRACTICED_CORE_DOMAIN" if attempts == 0 else "WEAK_TOPIC_REMEDIATION"
            action_items = [
                f"Complete 3–5 foundational {suggested_diff} practice questions in {topic_name}.",
                f"Review fundamental documentation and syntax guidelines for {topic_name}.",
                "Re-attempt any questions answered incorrectly to solidify concept retention.",
            ]
        elif 60.0 <= score < 75.0:
            priority_tier = "consolidation"
            rec_count = 3
            suggested_diff = "medium"
            reason_code = "CHALLENGE_ADVANCEMENT"
            action_items = [
                f"Solve 3 medium-level questions in {topic_name}.",
                "Practice under a timed environment (aim for under 45 seconds per MCQ).",
                "Target 80%+ accuracy on the next session to enter the proficient tier.",
            ]
        else:
            priority_tier = "maintenance"
            rec_count = 2
            suggested_diff = "hard"
            reason_code = "RETENTION_REFRESH"
            action_items = [
                f"Attempt 1–2 advanced/hard scenario questions in {topic_name}.",
                "Review edge-case architecture considerations and system design trade-offs.",
            ]

        plan_items.append(
            StudyPlanTopicItem(
                topic=topic_name,
                priority_tier=priority_tier,  # type: ignore
                current_mastery=score,
                recent_attempts_count=attempts,
                recommended_questions_count=rec_count,
                suggested_difficulty=suggested_diff,
                reason_code=reason_code,
                action_items=action_items,
            )
        )

    # Sort plan items: immediate_remediation first, then consolidation, then maintenance
    tier_order = {"immediate_remediation": 0, "consolidation": 1, "maintenance": 2}
    plan_items.sort(key=lambda x: (tier_order.get(x.priority_tier, 3), x.current_mastery))

    avg_mastery = (
        round(sum(m.mastery_score for m in masteries) / len(masteries), 1) if masteries else 0.0
    )
    remediation_count = sum(1 for p in plan_items if p.priority_tier == "immediate_remediation")
    consolidation_count = sum(1 for p in plan_items if p.priority_tier == "consolidation")

    summary = (
        f"Diagnostic study plan for {target_role}: Overall preparation mastery is currently {avg_mastery:.1f}%. "
        f"{remediation_count} topic(s) require immediate remediation, {consolidation_count} topic(s) are in consolidation, "
        f"and {len(plan_items) - remediation_count - consolidation_count} topic(s) have attained proficient maintenance."
    )

    log_recommendation_audit(
        db=db,
        user_id=user_id,
        recommendation_type="study_plan",
        target_id=target_role,
        rationale=summary,
        reason_code="STRUCTURED_STUDY_PLAN_GENERATION",
    )

    return StudyPlanResponse(
        user_id=user_id,
        target_role=target_role,
        overall_average_mastery=avg_mastery,
        summary=summary,
        topics=plan_items,
        generated_at=datetime.now(timezone.utc),
    )


def list_user_recommendation_audits(
    db: Session,
    user_id: int,
    skip: int = 0,
    limit: int = 20,
) -> Tuple[List[RecommendationAudit], int]:
    """Retrieve historical recommendation decisions for auditability and compliance."""
    count_query = select(func.count(RecommendationAudit.id)).where(RecommendationAudit.user_id == user_id)
    total = db.scalar(count_query) or 0

    audits = db.scalars(
        select(RecommendationAudit)
        .where(RecommendationAudit.user_id == user_id)
        .order_by(RecommendationAudit.created_at.desc())
        .offset(skip)
        .limit(limit)
    ).all()

    return list(audits), total
