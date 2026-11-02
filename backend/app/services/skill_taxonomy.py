"""Canonical skill dictionary, alias resolution, and taxonomy database seeding."""

import re
from typing import Dict, List, Optional, Tuple
from sqlalchemy.orm import Session
from app.models import Skill

DEFAULT_SKILL_TAXONOMY: Dict[str, Dict[str, object]] = {
    # Programming Languages
    "Python": {"category": "languages", "aliases": ["python3", "py3"]},
    "SQL": {"category": "languages", "aliases": ["structured query language"]},
    "JavaScript": {"category": "languages", "aliases": ["js", "es6", "ecmascript"]},
    "TypeScript": {"category": "languages", "aliases": ["ts"]},
    "HTML": {"category": "languages", "aliases": ["html5"]},
    "CSS": {"category": "languages", "aliases": ["css3"]},
    "Java": {"category": "languages", "aliases": ["core java"]},
    "C++": {"category": "languages", "aliases": ["cpp", "c plus plus"]},
    "Bash": {"category": "languages", "aliases": ["shell script", "shell scripting", "bash script"]},
    # Frameworks & Libraries
    "FastAPI": {"category": "frameworks", "aliases": ["fast api"]},
    "Flask": {"category": "frameworks", "aliases": []},
    "Django": {"category": "frameworks", "aliases": []},
    "React": {"category": "frameworks", "aliases": ["reactjs", "react.js"]},
    "Node.js": {"category": "frameworks", "aliases": ["nodejs", "node"]},
    "Express": {"category": "frameworks", "aliases": ["expressjs", "express.js"]},
    "Pandas": {"category": "frameworks", "aliases": []},
    "NumPy": {"category": "frameworks", "aliases": ["numpy array"]},
    "Scikit-Learn": {"category": "frameworks", "aliases": ["scikit learn", "sklearn"]},
    "PyTorch": {"category": "frameworks", "aliases": ["pytorch"]},
    "TensorFlow": {"category": "frameworks", "aliases": ["tf", "tensorflow"]},
    "Matplotlib": {"category": "frameworks", "aliases": []},
    "Seaborn": {"category": "frameworks", "aliases": []},
    # Databases & Storage
    "PostgreSQL": {"category": "databases", "aliases": ["postgres", "postgresql", "psql"]},
    "SQLite": {"category": "databases", "aliases": ["sqlite3"]},
    "MySQL": {"category": "databases", "aliases": []},
    "MongoDB": {"category": "databases", "aliases": ["mongo"]},
    "Redis": {"category": "databases", "aliases": []},
    # Developer Tools & Platforms
    "Docker": {"category": "tools", "aliases": ["docker compose", "containerization"]},
    "Git": {"category": "tools", "aliases": ["github", "gitlab", "version control"]},
    "Linux": {"category": "tools", "aliases": ["unix", "ubuntu"]},
    "REST APIs": {"category": "tools", "aliases": ["restful api", "rest api", "rest api development"]},
    "GraphQL": {"category": "tools", "aliases": []},
}

# Pre-compile lookup table mapping lowercase alias/name -> canonical name
LOOKUP_MAP: Dict[str, str] = {}
for canonical, data in DEFAULT_SKILL_TAXONOMY.items():
    LOOKUP_MAP[canonical.lower()] = canonical
    for alias in data.get("aliases", []):
        LOOKUP_MAP[alias.lower()] = canonical


def normalize_skill_name(raw_name: str) -> Optional[str]:
    """Map a raw skill string or alias to its canonical title."""
    clean = raw_name.strip().lower()
    return LOOKUP_MAP.get(clean, raw_name.strip().title())


def ensure_default_skills(db: Session) -> Dict[str, Skill]:
    """Seed or fetch the canonical skills in the database and return a name -> Skill map."""
    existing_skills = {s.canonical_name: s for s in db.query(Skill).all()}

    for canonical, data in DEFAULT_SKILL_TAXONOMY.items():
        if canonical not in existing_skills:
            skill = Skill(
                canonical_name=canonical,
                category=data["category"],
                aliases=data["aliases"],
            )
            db.add(skill)
            existing_skills[canonical] = skill

    db.commit()
    return existing_skills

