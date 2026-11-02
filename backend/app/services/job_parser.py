"""Job description parsing, skill requirement extraction, and synthetic demo job seeding."""

import re
from typing import Dict, List, Optional, Set, Tuple
from sqlalchemy.orm import Session
from app.models import Job, JobSkill, Skill
from app.services.skill_taxonomy import LOOKUP_MAP, ensure_default_skills, normalize_skill_name

PREFERRED_PATTERNS = re.compile(
    r"\b(?:preferred|nice\s+to\s+have|bonus|desired|plus|good\s+to\s+have|optional\s+qualifications|advantages?)\b",
    re.IGNORECASE,
)
REQUIRED_PATTERNS = re.compile(
    r"\b(?:required|requirements|must\s+have|minimum\s+qualifications|basic\s+qualifications|prerequisites|core\s+requirements)\b",
    re.IGNORECASE,
)


def parse_job_skills(description: str) -> Tuple[List[str], List[str]]:
    """Parse a job description to identify required and preferred canonical skills.

    Returns:
        (required_skills, preferred_skills)
    """
    if not description:
        return [], []

    lines = [l.strip() for l in description.split("\n") if l.strip()]

    is_in_preferred_section = False
    required_skills: Set[str] = set()
    preferred_skills: Set[str] = set()

    for line in lines:
        if PREFERRED_PATTERNS.search(line):
            is_in_preferred_section = True
        elif REQUIRED_PATTERNS.search(line):
            is_in_preferred_section = False

        # Scan for canonical skill mentions on this line
        for alias_lower, canonical in LOOKUP_MAP.items():
            pattern = re.compile(rf"\b{re.escape(alias_lower)}\b", re.IGNORECASE)
            if pattern.search(line):
                if is_in_preferred_section:
                    # If not already required, add to preferred
                    if canonical not in required_skills:
                        preferred_skills.add(canonical)
                else:
                    required_skills.add(canonical)
                    # If previously marked preferred, upgrade to required
                    if canonical in preferred_skills:
                        preferred_skills.remove(canonical)

    return sorted(list(required_skills)), sorted(list(preferred_skills))


SYNTHETIC_BENCHMARK_JOBS = [
    {
        "title": "Junior Python Developer (Demo Fixture)",
        "company": "Synthetic Placement Partner A",
        "description": (
            "Job Summary:\n"
            "Entry-level Python software engineering role for placement preparation.\n\n"
            "Requirements:\n"
            "Must have solid knowledge of Python, FastAPI, and SQL.\n"
            "Experience with Git version control.\n\n"
            "Preferred Qualifications:\n"
            "Hands-on exposure to Docker or PostgreSQL is a bonus."
        ),
        "source_url": "demo://synthetic/junior-python-developer",
        "required_skills": ["Python", "FastAPI", "SQL", "Git"],
        "preferred_skills": ["Docker", "PostgreSQL"],
    },
    {
        "title": "Entry-Level Data Analyst (Demo Fixture)",
        "company": "Synthetic Placement Partner B",
        "description": (
            "Job Summary:\n"
            "Junior Data Analyst position focused on data cleaning and reporting.\n\n"
            "Requirements:\n"
            "Strong fundamentals in Python, SQL, and Pandas.\n\n"
            "Preferred Qualifications:\n"
            "Familiarity with Scikit-Learn or Matplotlib is a plus."
        ),
        "source_url": "demo://synthetic/entry-level-data-analyst",
        "required_skills": ["Python", "SQL", "Pandas"],
        "preferred_skills": ["Scikit-Learn", "Matplotlib"],
    },
]


def seed_synthetic_jobs(db: Session) -> List[Job]:
    """Seed or update explicitly marked synthetic benchmark jobs."""
    skill_map = ensure_default_skills(db)
    seeded_jobs: List[Job] = []

    for item in SYNTHETIC_BENCHMARK_JOBS:
        existing = db.query(Job).filter(Job.source_url == item["source_url"]).first()
        if not existing:
            job = Job(
                user_id=None,  # Public system job
                title=item["title"],
                company=item["company"],
                description=item["description"],
                source_url=item["source_url"],
                is_synthetic=True,
                is_active=True,
            )
            db.add(job)
            db.flush()

            # Attach required skills
            for req_name in item["required_skills"]:
                s = skill_map.get(req_name)
                if s:
                    db.add(JobSkill(job_id=job.id, skill_id=s.id, is_required=True))

            # Attach preferred skills
            for pref_name in item["preferred_skills"]:
                s = skill_map.get(pref_name)
                if s:
                    db.add(JobSkill(job_id=job.id, skill_id=s.id, is_required=False))

            seeded_jobs.append(job)
        else:
            seeded_jobs.append(existing)

    db.commit()
    return seeded_jobs

