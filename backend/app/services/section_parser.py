"""Deterministic resume section segmentation, skill extraction, and evidence snippet linking."""

import re
from typing import Dict, List, Optional, Tuple
from app.services.skill_taxonomy import DEFAULT_SKILL_TAXONOMY, LOOKUP_MAP

# Canonical section header patterns
SECTION_PATTERNS = {
    "skills": re.compile(
        r"^(?:technical\s+|key\s+|core\s+)?(?:skills|competencies|technologies|tech\s+stack|tools\s+&\s+technologies)\b",
        re.IGNORECASE | re.MULTILINE,
    ),
    "experience": re.compile(
        r"^(?:work\s+|professional\s+|relevant\s+)?(?:experience|employment|work\s+history|internships?)\b",
        re.IGNORECASE | re.MULTILINE,
    ),
    "projects": re.compile(
        r"^(?:key\s+|academic\s+|personal\s+|technical\s+)?(?:projects|project\s+work)\b",
        re.IGNORECASE | re.MULTILINE,
    ),
    "education": re.compile(
        r"^(?:education|academic\s+background|qualifications|academic\s+history|degrees?)\b",
        re.IGNORECASE | re.MULTILINE,
    ),
    "summary": re.compile(
        r"^(?:professional\s+)?(?:summary|profile|objective|about\s+me)\b",
        re.IGNORECASE | re.MULTILINE,
    ),
}

# Negation prefixes to prevent extracting skills the candidate explicitly does not possess
NEGATION_PATTERNS = [
    re.compile(
        r"\b(?:no|not|never|lack|lacking|minimal|without|little)\s+(?:experience|experienced|knowledge|familiar|familiarity|understanding|proficient|using|used)?\s*(?:with|in|of|at)?\s*$",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(?:interested\s+in|willing\s+to|planning\s+to|aiming\s+to|want\s+to)\s+learn\s*$",
        re.IGNORECASE,
    ),
]


def segment_resume_sections(text: str) -> Dict[str, str]:
    """Segment resume text into standard sections based on detected heading lines."""
    if not text:
        return {"summary": "", "skills": "", "experience": "", "projects": "", "education": "", "other": ""}

    lines = text.split("\n")
    sections: Dict[str, List[str]] = {
        "summary": [],
        "skills": [],
        "experience": [],
        "projects": [],
        "education": [],
        "other": [],
    }

    current_section = "other"

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue

        # Check if line matches a known section heading (typically short, <= 45 chars)
        matched_section = None
        if len(stripped) <= 45:
            # Strip trailing colons or dashes (e.g. "Skills:", "Work Experience -")
            heading_candidate = re.sub(r"[:\-_]+$", "", stripped).strip()
            for sec_name, pattern in SECTION_PATTERNS.items():
                if pattern.match(heading_candidate):
                    matched_section = sec_name
                    break

        if matched_section:
            current_section = matched_section
        else:
            sections[current_section].append(stripped)

    return {sec: "\n".join(content_lines).strip() for sec, content_lines in sections.items()}


def is_negated_mention(preceding_text: str) -> bool:
    """Check if the context immediately preceding a skill mention contains negation."""
    snippet = preceding_text[-60:].strip()
    for neg_regex in NEGATION_PATTERNS:
        if neg_regex.search(snippet):
            return True
    return False


def extract_skills_with_evidence(text: str, sections: Optional[Dict[str, str]] = None) -> List[Dict[str, object]]:
    """Deterministically extract skills from text, link evidence sentences, and assign confidence."""
    if not text:
        return []

    if sections is None:
        sections = segment_resume_sections(text)

    # Break full text into sentences/lines for snippet location
    raw_lines = [l.strip() for l in text.split("\n") if l.strip()]

    extracted_skills: Dict[str, Dict[str, object]] = {}

    for alias_lower, canonical in LOOKUP_MAP.items():
        # Word boundary matching with optional punctuation allowance
        escaped_alias = re.escape(alias_lower)
        pattern = re.compile(rf"\b{escaped_alias}\b", re.IGNORECASE)

        for line in raw_lines:
            match = pattern.search(line)
            if match:
                # Check for negation in the text preceding the match within the line
                start_idx = match.start()
                preceding = line[:start_idx]
                if is_negated_mention(preceding):
                    continue

                # Determine section provenance for confidence scoring
                confidence = 0.70
                if canonical in extracted_skills:
                    # Keep highest confidence if already found
                    confidence = max(confidence, extracted_skills[canonical]["confidence_score"])

                if sections.get("skills") and line in sections["skills"]:
                    confidence = 1.00
                elif sections.get("projects") and line in sections["projects"]:
                    confidence = max(confidence, 0.90)
                elif sections.get("experience") and line in sections["experience"]:
                    confidence = max(confidence, 0.85)

                # Trim line to a clean evidence snippet (max 180 chars)
                snippet = line
                if len(snippet) > 180:
                    snippet = snippet[:177] + "..."

                extracted_skills[canonical] = {
                    "canonical_name": canonical,
                    "evidence_snippet": snippet,
                    "confidence_score": confidence,
                    "is_auto_extracted": True,
                    "is_user_confirmed": False,
                }
                break

    return list(extracted_skills.values())
