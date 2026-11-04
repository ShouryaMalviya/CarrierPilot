"""Service layer for aggregating learner progress, practice streaks, and dashboard telemetry."""

from datetime import date, datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import (
    InterviewSession,
    Job,
    PracticeAttempt,
    PracticeSession,
    Profile,
    Question,
    Resume,
)
from app.schemas.progress import (
    DailyActivity,
    DashboardProgressResponse,
    DashboardTopicMastery,
    NextRecommendedAction,
    ReadinessBreakdown,
    StreakResponse,
)
from app.services import mastery_service
from app.services.recommendation_service import get_user_target_role


def calculate_user_streak(
    db: Session,
    user_id: int,
) -> Tuple[int, int, Optional[str]]:
    """Calculate current and longest consecutive daily practice streak.

    Returns:
        (current_streak_days, longest_streak_days, last_active_date_str)
    """
    attempt_timestamps = db.scalars(
        select(PracticeAttempt.created_at)
        .where(PracticeAttempt.user_id == user_id)
        .order_by(PracticeAttempt.created_at.desc())
    ).all()

    if not attempt_timestamps:
        return 0, 0, None

    # Extract distinct calendar dates in UTC
    distinct_dates = sorted(
        list({ts.date() for ts in attempt_timestamps if ts is not None}),
        reverse=True,
    )
    if not distinct_dates:
        return 0, 0, None

    last_active_date = distinct_dates[0]
    today = datetime.now(timezone.utc).date()
    yesterday = today - timedelta(days=1)

    # Calculate Current Streak
    current_streak = 0
    if last_active_date in (today, yesterday):
        current_streak = 1
        expected_date = last_active_date - timedelta(days=1)
        for d in distinct_dates[1:]:
            if d == expected_date:
                current_streak += 1
                expected_date = d - timedelta(days=1)
            elif d < expected_date:
                break
    else:
        current_streak = 0

    # Calculate Longest Streak
    sorted_asc_dates = sorted(distinct_dates)
    longest_streak = 1
    curr_run = 1

    for i in range(1, len(sorted_asc_dates)):
        if sorted_asc_dates[i] == sorted_asc_dates[i - 1] + timedelta(days=1):
            curr_run += 1
            if curr_run > longest_streak:
                longest_streak = curr_run
        else:
            curr_run = 1

    return current_streak, longest_streak, last_active_date.isoformat()


def get_daily_activity_timeline(
    db: Session,
    user_id: int,
    days: int = 14,
) -> List[DailyActivity]:
    """Retrieve daily practice activity for the last N calendar days."""
    today = datetime.now(timezone.utc).date()
    start_date = today - timedelta(days=days - 1)

    # Initialize full date map with zeros
    activity_map: Dict[date, Dict[str, int]] = {
        (start_date + timedelta(days=i)): {"attempts": 0, "correct": 0, "duration": 0}
        for i in range(days)
    }

    start_datetime = datetime.combine(start_date, datetime.min.time(), tzinfo=timezone.utc)
    attempts = db.execute(
        select(
            PracticeAttempt.created_at,
            PracticeAttempt.is_correct,
            PracticeAttempt.duration_seconds,
        ).where(
            PracticeAttempt.user_id == user_id,
            PracticeAttempt.created_at >= start_datetime,
        )
    ).all()

    for created_at, is_corr, duration in attempts:
        if created_at:
            att_date = created_at.date()
            if att_date in activity_map:
                activity_map[att_date]["attempts"] += 1
                if is_corr:
                    activity_map[att_date]["correct"] += 1
                activity_map[att_date]["duration"] += duration or 0

    return [
        DailyActivity(
            date=d.isoformat(),
            attempt_count=data["attempts"],
            correct_count=data["correct"],
            duration_seconds=data["duration"],
        )
        for d, data in sorted(activity_map.items(), key=lambda x: x[0])
    ]


def compute_topic_mastery_cards(
    db: Session,
    user_id: int,
) -> List[DashboardTopicMastery]:
    """Compile topic mastery cards with status tiers and accuracy metrics."""
    records = mastery_service.get_user_topic_masteries(db, user_id)

    # Calculate overall attempt accuracy per topic
    topic_attempts = db.execute(
        select(Question.topic, PracticeAttempt.is_correct)
        .join(Question, PracticeAttempt.question_id == Question.id)
        .where(PracticeAttempt.user_id == user_id)
    ).all()

    topic_counts: Dict[str, Dict[str, int]] = {}
    for topic, is_corr in topic_attempts:
        if topic not in topic_counts:
            topic_counts[topic] = {"total": 0, "correct": 0}
        topic_counts[topic]["total"] += 1
        if is_corr:
            topic_counts[topic]["correct"] += 1

    cards: List[DashboardTopicMastery] = []
    for rec in records:
        topic_name = rec.topic
        attempts_count = rec.recent_attempts_count
        score = rec.mastery_score

        counts = topic_counts.get(topic_name, {"total": 0, "correct": 0})
        acc_pct = (
            round((counts["correct"] / counts["total"]) * 100.0, 1)
            if counts["total"] > 0
            else 0.0
        )

        if attempts_count == 0:
            status_tier = "unattempted"
        elif score >= 75.0:
            status_tier = "proficient"
        elif score >= 60.0:
            status_tier = "developing"
        else:
            status_tier = "needs_practice"

        cards.append(
            DashboardTopicMastery(
                topic=topic_name,
                mastery_score=score,
                recent_attempts_count=attempts_count,
                accuracy_percentage=acc_pct,
                status_tier=status_tier,  # type: ignore
                reason_codes=rec.reason_codes or [],
            )
        )

    return cards


def compute_readiness_breakdown(
    db: Session,
    user_id: int,
    target_role: str,
    masteries: List[DashboardTopicMastery],
) -> ReadinessBreakdown:
    """Compute multi-factor placement readiness index."""
    # Factor 1: Resume Profile Quality (30% weight)
    resume = db.scalar(
        select(Resume).where(Resume.user_id == user_id).order_by(Resume.created_at.desc())
    )
    if resume and resume.parse_status == "completed":
        resume_score = 100.0
    elif resume:
        resume_score = 50.0
    else:
        resume_score = 0.0

    # Factor 2: Practice Mastery (40% weight)
    if masteries:
        practice_score = round(sum(m.mastery_score for m in masteries) / len(masteries), 1)
    else:
        practice_score = 0.0

    # Factor 3: Job Matching Exploration (15% weight)
    job_count = db.scalar(select(func.count(Job.id)).where(Job.user_id == user_id)) or 0
    job_score = 100.0 if job_count >= 1 else 0.0

    # Factor 4: Mock Interview Completion (15% weight)
    interview_count = (
        db.scalar(
            select(func.count(InterviewSession.id)).where(
                InterviewSession.user_id == user_id,
                InterviewSession.status == "completed",
            )
        )
        or 0
    )
    interview_score = 100.0 if interview_count >= 1 else 0.0

    # Composite weighted readiness score
    overall = (
        0.40 * practice_score
        + 0.30 * resume_score
        + 0.15 * job_score
        + 0.15 * interview_score
    )
    overall = round(max(0.0, min(100.0, overall)), 1)

    if overall >= 75.0:
        level = "placement_ready"
    elif overall >= 50.0:
        level = "developing"
    else:
        level = "beginner"

    return ReadinessBreakdown(
        overall_readiness_score=overall,
        profile_resume_score=resume_score,
        practice_mastery_score=practice_score,
        job_matching_score=job_score,
        mock_interview_score=interview_score,
        readiness_level=level,  # type: ignore
    )


def determine_next_action(
    readiness: ReadinessBreakdown,
    masteries: List[DashboardTopicMastery],
) -> NextRecommendedAction:
    """Select high-impact action card for the main dashboard interface."""
    # 1. Check if user needs to upload a resume
    if readiness.profile_resume_score == 0.0:
        return NextRecommendedAction(
            action_type="upload_resume",
            title="Upload Your Resume",
            description="Upload your resume to extract canonical skills and discover personalized job matches.",
            target_url="/resumes",
        )

    # 2. Check for topics needing immediate remediation
    weak_topics = [m for m in masteries if m.status_tier == "needs_practice"]
    if weak_topics:
        weak_topics.sort(key=lambda x: x.mastery_score)
        target = weak_topics[0]
        return NextRecommendedAction(
            action_type="remediate_weak_topic",
            title=f"Remediate {target.topic}",
            description=f"Your estimated mastery in {target.topic} is {target.mastery_score:.1f}%. Practice fundamentals to rebuild proficiency.",
            target_topic=target.topic,
            target_url=f"/practice?topic={target.topic}",
        )

    # 3. Check for unattempted topics
    unattempted = [m for m in masteries if m.status_tier == "unattempted"]
    if unattempted:
        target = unattempted[0]
        return NextRecommendedAction(
            action_type="start_practice",
            title=f"Start Practice in {target.topic}",
            description=f"Calibrate your diagnostic baseline with a short 5-question practice session in {target.topic}.",
            target_topic=target.topic,
            target_url=f"/practice?topic={target.topic}",
        )

    # 4. Check for developing topics to advance
    developing = [m for m in masteries if m.status_tier == "developing"]
    if developing:
        developing.sort(key=lambda x: x.mastery_score)
        target = developing[0]
        return NextRecommendedAction(
            action_type="advance_challenge",
            title=f"Advance Mastery in {target.topic}",
            description=f"Your current mastery is {target.mastery_score:.1f}%. Solve medium/hard problems to reach the 75%+ proficient tier.",
            target_topic=target.topic,
            target_url=f"/practice?topic={target.topic}",
        )

    # 5. Check if mock interview is pending
    if readiness.mock_interview_score == 0.0:
        return NextRecommendedAction(
            action_type="mock_interview",
            title="Complete a Technical Mock Interview",
            description="Your diagnostic question mastery is strong. Test conceptual articulation in a typed mock interview.",
            target_url="/interviews",
        )

    # 6. Default: explore matched placements
    return NextRecommendedAction(
        action_type="explore_jobs",
        title="Review Placement Matches",
        description="Your preparation metrics are well-developed. Inspect role skill gaps and company alignments.",
        target_url="/jobs",
    )


def get_dashboard_progress(
    db: Session,
    user_id: int,
) -> DashboardProgressResponse:
    """Generate consolidated telemetry, streak, readiness, and action cards for learner dashboard."""
    target_role = get_user_target_role(db, user_id)

    # Streaks and activity
    current_streak, longest_streak, _ = calculate_user_streak(db, user_id)
    timeline = get_daily_activity_timeline(db, user_id, days=14)

    # Topic Masteries
    topic_cards = compute_topic_mastery_cards(db, user_id)

    # Readiness
    readiness = compute_readiness_breakdown(db, user_id, target_role, topic_cards)

    # Total attempts & accuracy telemetry
    attempts_stats = db.execute(
        select(
            func.count(PracticeAttempt.id),
            func.sum(PracticeAttempt.duration_seconds),
        ).where(PracticeAttempt.user_id == user_id)
    ).first()

    total_attempts = attempts_stats[0] or 0
    total_time = attempts_stats[1] or 0

    correct_attempts = (
        db.scalar(
            select(func.count(PracticeAttempt.id)).where(
                PracticeAttempt.user_id == user_id,
                PracticeAttempt.is_correct.is_(True),
            )
        )
        or 0
    )
    overall_accuracy = (
        round((correct_attempts / total_attempts) * 100.0, 1)
        if total_attempts > 0
        else 0.0
    )

    # Practice sessions telemetry
    completed_sessions = (
        db.scalar(
            select(func.count(PracticeSession.id)).where(
                PracticeSession.user_id == user_id,
                PracticeSession.status == "completed",
            )
        )
        or 0
    )
    active_sessions = (
        db.scalar(
            select(func.count(PracticeSession.id)).where(
                PracticeSession.user_id == user_id,
                PracticeSession.status == "in_progress",
            )
        )
        or 0
    )

    # Next Action Card
    next_action = determine_next_action(readiness, topic_cards)

    return DashboardProgressResponse(
        user_id=user_id,
        target_role=target_role,
        readiness=readiness,
        streak_days=current_streak,
        longest_streak_days=longest_streak,
        total_attempts=total_attempts,
        correct_attempts=correct_attempts,
        overall_accuracy_percentage=overall_accuracy,
        total_practice_time_seconds=total_time,
        completed_sessions_count=completed_sessions,
        active_sessions_count=active_sessions,
        topic_masteries=topic_cards,
        activity_timeline=timeline,
        next_action=next_action,
        generated_at=datetime.now(timezone.utc),
    )

