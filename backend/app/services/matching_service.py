"""Lexical matching service combining TF-IDF cosine similarity and normalized skill gap analysis."""

import math
import re
from collections import Counter
from typing import List, Optional, Set, Tuple
from sqlalchemy.orm import Session, joinedload

from app.models import Job, JobSkill, Resume, ResumeSkill
from app.schemas.matching import (
    DEFAULT_MATCHING_DISCLAIMER,
    BatchMatchItem,
    BatchMatchResponse,
    LexicalMatchResponse,
    MatchScoreBreakdown,
    SkillGapBreakdown,
)

# Standard English stop words for tokenization
STOP_WORDS: Set[str] = {
    "a", "about", "above", "after", "again", "against", "all", "am", "an", "and",
    "any", "are", "aren't", "as", "at", "be", "because", "been", "before", "being",
    "below", "between", "both", "but", "by", "can", "cannot", "could", "couldn't",
    "did", "didn't", "do", "does", "doesn't", "doing", "don't", "down", "during",
    "each", "few", "for", "from", "further", "had", "hadn't", "has", "hasn't",
    "have", "haven't", "having", "he", "he'd", "he'll", "he's", "her", "here",
    "here's", "hers", "herself", "him", "himself", "his", "how", "how's", "i",
    "i'd", "i'll", "i'm", "i've", "if", "in", "into", "is", "isn't", "it", "it's",
    "its", "itself", "let's", "me", "more", "most", "mustn't", "my", "myself",
    "no", "nor", "not", "of", "off", "on", "once", "only", "or", "other", "ought",
    "our", "ours", "ourselves", "out", "over", "own", "same", "shan't", "she",
    "she'd", "she'll", "she's", "should", "shouldn't", "so", "some", "such",
    "than", "that", "that's", "the", "their", "theirs", "them", "themselves",
    "then", "there", "there's", "these", "they", "they'd", "they'll", "they're",
    "they've", "this", "those", "through", "to", "too", "under", "until", "up",
    "very", "was", "wasn't", "we", "we'd", "we'll", "we're", "we've", "were",
    "weren't", "what", "what's", "when", "when's", "where", "where's", "which",
    "while", "who", "who's", "whom", "why", "why's", "with", "won't", "would",
    "wouldn't", "you", "you'd", "you'll", "you're", "you've", "your", "yours",
    "yourself", "yourselves",
}

TOKEN_PATTERN = re.compile(r"\b[a-zA-Z0-9_+#\.\-]+\b")


def tokenize_text(text: str) -> List[str]:
    """Tokenize text into lowercase alphanumeric tokens excluding standard stop words."""
    if not text:
        return []
    raw_tokens = TOKEN_PATTERN.findall(text.lower())
    return [t for t in raw_tokens if t not in STOP_WORDS and len(t) > 1]


def compute_tfidf_similarity(
    text_a: str,
    text_b: str,
    use_sklearn: bool = False,
) -> float:
    """Compute cosine similarity between two texts using TF-IDF weighting.

    Uses scikit-learn standard smooth IDF formulation:
    IDF(t) = ln((1 + N) / (1 + DF(t))) + 1.0
    Cosine similarity = (u . v) / (||u|| * ||v||)

    Returns:
        float bounded in [0.0, 1.0], rounded to 4 decimal places.
    """
    if not text_a or not text_b or not text_a.strip() or not text_b.strip():
        return 0.0

    if use_sklearn:
        try:
            from sklearn.feature_extraction.text import TfidfVectorizer
            from sklearn.metrics.pairwise import cosine_similarity

            vec = TfidfVectorizer(stop_words="english", token_pattern=r"(?u)\b\w+\b")
            mat = vec.fit_transform([text_a, text_b])
            sim = float(cosine_similarity(mat[0:1], mat[1:2])[0][0])
            return round(max(0.0, min(1.0, sim)), 4)
        except Exception:
            pass  # Fall through to native calculation

    tokens_a = tokenize_text(text_a)
    tokens_b = tokenize_text(text_b)

    if not tokens_a or not tokens_b:
        return 0.0

    counts_a = Counter(tokens_a)
    counts_b = Counter(tokens_b)

    vocab = set(counts_a.keys()).union(set(counts_b.keys()))
    num_docs = 2

    vec_a: List[float] = []
    vec_b: List[float] = []

    for term in vocab:
        df = (1 if term in counts_a else 0) + (1 if term in counts_b else 0)
        # scikit-learn standard smooth IDF
        idf = math.log((1 + num_docs) / (1 + df)) + 1.0
        vec_a.append(counts_a.get(term, 0) * idf)
        vec_b.append(counts_b.get(term, 0) * idf)

    dot_product = sum(a * b for a, b in zip(vec_a, vec_b))
    norm_a = math.sqrt(sum(a * a for a in vec_a))
    norm_b = math.sqrt(sum(b * b for b in vec_b))

    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0

    cosine_sim = dot_product / (norm_a * norm_b)
    return round(max(0.0, min(1.0, cosine_sim)), 4)


def compute_skill_gap(
    resume_skills: Set[str],
    required_skills: Set[str],
    preferred_skills: Set[str],
) -> Tuple[SkillGapBreakdown, float, float]:
    """Calculate matched and missing skills across required and preferred categories.

    Returns:
        (SkillGapBreakdown, required_coverage, preferred_coverage)
    """
    matched_required = sorted(list(resume_skills.intersection(required_skills)))
    missing_required = sorted(list(required_skills.difference(resume_skills)))

    matched_preferred = sorted(list(resume_skills.intersection(preferred_skills)))
    missing_preferred = sorted(list(preferred_skills.difference(resume_skills)))

    all_job_skills = required_skills.union(preferred_skills)
    additional_skills = sorted(list(resume_skills.difference(all_job_skills)))

    # Coverage metrics
    if len(required_skills) > 0:
        req_coverage = round(len(matched_required) / len(required_skills), 4)
    else:
        req_coverage = 1.0

    if len(preferred_skills) > 0:
        pref_coverage = round(len(matched_preferred) / len(preferred_skills), 4)
    else:
        pref_coverage = 1.0

    breakdown = SkillGapBreakdown(
        matched_required=matched_required,
        missing_required=missing_required,
        matched_preferred=matched_preferred,
        missing_preferred=missing_preferred,
        additional_skills=additional_skills,
    )

    return breakdown, req_coverage, pref_coverage


def calculate_lexical_match(
    resume_text: str,
    resume_skills: Set[str],
    job_text: str,
    required_skills: Set[str],
    preferred_skills: Set[str],
    use_sklearn: bool = False,
) -> Tuple[MatchScoreBreakdown, SkillGapBreakdown]:
    """Calculate composite lexical match score and skill gap breakdown.

    Formula (Lexical Baseline):
        overall_score = (0.60 * req_coverage + 0.20 * pref_coverage + 0.20 * tfidf_sim) * 100
    """
    tfidf_sim = compute_tfidf_similarity(resume_text, job_text, use_sklearn=use_sklearn)
    skill_gap, req_cov, pref_cov = compute_skill_gap(
        resume_skills=resume_skills,
        required_skills=required_skills,
        preferred_skills=preferred_skills,
    )

    overall_raw = (0.60 * req_cov + 0.20 * pref_cov + 0.20 * tfidf_sim) * 100.0
    overall_score = round(max(0.0, min(100.0, overall_raw)), 2)

    scores = MatchScoreBreakdown(
        required_coverage=req_cov,
        preferred_coverage=pref_cov,
        tfidf_similarity=tfidf_sim,
        overall_score=overall_score,
    )

    return scores, skill_gap


def extract_resume_data(resume: Resume) -> Tuple[str, Set[str]]:
    """Extract raw text and verified/extracted canonical skill set from a Resume model."""
    skills = {
        rs.skill.canonical_name
        for rs in resume.resume_skills
        if rs.skill and rs.skill.canonical_name
    }
    text = ""
    if resume.parsed_content and isinstance(resume.parsed_content, dict):
        text = resume.parsed_content.get("text", "") or ""
        if not text.strip() and "sections" in resume.parsed_content:
            sections = resume.parsed_content["sections"]
            if isinstance(sections, dict):
                text = " ".join(v for v in sections.values() if isinstance(v, str))

    if not text.strip():
        # Fallback to skills if no body text is available
        text = " ".join(skills)

    return text, skills


def extract_job_data(job: Job) -> Tuple[str, Set[str], Set[str]]:
    """Extract description text and required/preferred canonical skill sets from a Job model."""
    req_skills: Set[str] = set()
    pref_skills: Set[str] = set()

    for js in job.job_skills:
        if js.skill and js.skill.canonical_name:
            if js.is_required:
                req_skills.add(js.skill.canonical_name)
            else:
                pref_skills.add(js.skill.canonical_name)

    text = job.description or ""
    return text, req_skills, pref_skills


def match_resume_to_job(
    resume: Resume,
    job: Job,
    use_sklearn: bool = False,
) -> LexicalMatchResponse:
    """Perform single-job lexical match evaluation between a Resume and Job model."""
    resume_text, resume_skills = extract_resume_data(resume)
    job_text, req_skills, pref_skills = extract_job_data(job)

    scores, skill_gap = calculate_lexical_match(
        resume_text=resume_text,
        resume_skills=resume_skills,
        job_text=job_text,
        required_skills=req_skills,
        preferred_skills=pref_skills,
        use_sklearn=use_sklearn,
    )

    return LexicalMatchResponse(
        resume_id=resume.id,
        job_id=job.id,
        job_title=job.title,
        company=job.company,
        scores=scores,
        skill_gap=skill_gap,
        disclaimer=DEFAULT_MATCHING_DISCLAIMER,
    )


def match_resume_to_all_jobs(
    db: Session,
    resume: Resume,
    accessible_jobs: List[Job],
    limit: int = 50,
    offset: int = 0,
    use_sklearn: bool = False,
) -> BatchMatchResponse:
    """Evaluate a candidate resume against all accessible jobs, returning matches ranked by score."""
    resume_text, resume_skills = extract_resume_data(resume)
    batch_items: List[BatchMatchItem] = []

    for job in accessible_jobs:
        job_text, req_skills, pref_skills = extract_job_data(job)
        scores, skill_gap = calculate_lexical_match(
            resume_text=resume_text,
            resume_skills=resume_skills,
            job_text=job_text,
            required_skills=req_skills,
            preferred_skills=pref_skills,
            use_sklearn=use_sklearn,
        )

        batch_items.append(
            BatchMatchItem(
                job_id=job.id,
                job_title=job.title,
                company=job.company,
                is_synthetic=job.is_synthetic,
                overall_score=scores.overall_score,
                required_coverage=scores.required_coverage,
                preferred_coverage=scores.preferred_coverage,
                tfidf_similarity=scores.tfidf_similarity,
                missing_required_count=len(skill_gap.missing_required),
                missing_required=skill_gap.missing_required,
            )
        )

    # Sort descending by overall_score, then tie-break by required_coverage
    batch_items.sort(key=lambda item: (item.overall_score, item.required_coverage), reverse=True)

    total = len(batch_items)
    paged = batch_items[offset : offset + limit]

    return BatchMatchResponse(
        resume_id=resume.id,
        total_jobs_evaluated=total,
        matches=paged,
        disclaimer=DEFAULT_MATCHING_DISCLAIMER,
    )
