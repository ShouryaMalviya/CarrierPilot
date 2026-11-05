"""Deterministic rubric-based coaching and evaluation service for typed mock interviews."""

import re
from typing import Dict, List, Optional, Set, Tuple
from app.schemas.rubric import DimensionScore, RubricFeedback

RUBRIC_VERSION = "1.0.0"

DIMENSION_LABELS = {
    "relevance": "Relevance to Prompt",
    "technical_correctness": "Technical Correctness",
    "completeness": "Completeness & Edge Cases",
    "structure": "Structure & Communication",
    "use_of_examples": "Use of Concrete Examples",
}

# Stopwords to filter out during question prompt keyword extraction
STOPWORDS = {
    "a", "about", "above", "after", "again", "against", "all", "am", "an", "and", "any", "are",
    "aren't", "as", "at", "be", "because", "been", "before", "being", "below", "between", "both",
    "but", "by", "can", "can't", "cannot", "could", "couldn't", "did", "didn't", "do", "does",
    "doesn't", "doing", "don't", "down", "during", "each", "explain", "describe", "detail", "discuss",
    "few", "for", "from", "further", "had", "hadn't", "has", "hasn't", "have", "haven't", "having",
    "he", "he'd", "he'll", "he's", "her", "here", "here's", "hers", "herself", "him", "himself",
    "his", "how", "how's", "i", "i'd", "i'll", "i'm", "i've", "if", "in", "into", "is", "isn't",
    "it", "it's", "its", "itself", "let's", "me", "more", "most", "mustn't", "my", "myself",
    "no", "nor", "not", "of", "off", "on", "once", "only", "or", "other", "ought", "our", "ours",
    "ourselves", "out", "over", "own", "same", "shan't", "she", "she'd", "she'll", "she's",
    "should", "shouldn't", "so", "some", "such", "than", "that", "that's", "the", "their",
    "theirs", "them", "themselves", "then", "there", "there's", "these", "they", "they'd",
    "they'll", "they're", "they've", "this", "those", "through", "to", "too", "under", "until",
    "up", "very", "was", "wasn't", "we", "we'd", "we'll", "we're", "we've", "were", "weren't",
    "what", "what's", "when", "when's", "where", "where's", "which", "while", "who", "who's",
    "whom", "why", "why's", "with", "won't", "would", "wouldn't", "you", "you'd", "you'll",
    "you're", "you've", "your", "yours", "yourself", "yourselves", "would", "design", "outline",
}

# Domain technical terms catalog for validity check
TECHNICAL_TERMS = {
    # Architecture & Distributed Systems
    "crdt", "operational transformation", "ot", "websocket", "websockets", "sse", "server-sent events",
    "long polling", "event-driven", "idempotent", "idempotency", "broker", "dead letter", "dlq",
    "circuit breaker", "bulkhead", "backoff", "exponential backoff", "sharding", "replication",
    "partitioning", "consistency", "availability", "partition tolerance", "cap theorem",
    "load balancer", "horizontal scaling", "vertical scaling", "cache invalidation", "write-through",
    "cache-aside", "write-back", "ttl", "rate limit", "rate limiting", "token bucket", "leaky bucket",
    "sliding window", "sliding window counter", "sliding window log", "bloom filter", "distributed lock",
    "two-phase commit", "saga pattern", "grpc", "protobuf", "graphql", "rest", "microservices",
    "microservice", "cqrs", "event sourcing", "concurrency", "distributed", "snapshot", "snapshotting",
    # Database & Storage
    "acid", "mvcc", "wal", "write-ahead", "write ahead log", "b-tree", "b+ tree", "lsm tree",
    "index", "indexing", "composite index", "read replica", "read replicas", "replication lag",
    "primary-replica", "foreign key", "transaction", "isolation level", "read committed",
    "repeatable read", "serializable", "dirty read", "phantom read", "redis", "postgresql", "postgres",
    "mysql", "mongodb", "cassandra", "dynamodb", "s3", "blob storage", "connection pooling",
    "table lock", "row lock", "optimistic concurrency", "pessimistic locking",
    # Algorithms & Data Structures
    "hash map", "hash table", "min-heap", "max-heap", "priority queue", "binary search tree",
    "trie", "graph", "lru", "lfu", "time complexity", "space complexity", "o(1)", "o(n)", "o(log n)",
    "amortized", "mutex", "lock", "thread-safe", "atomic", "race condition", "deadlock",
    # Frontend
    "virtual dom", "reconciliation", "bundle", "webpack", "vite", "module federation",
    "shadow dom", "aria", "semantic html", "wcag", "keyboard navigation", "layout thrashing",
    "reflow", "repaint", "debounce", "throttle", "memoization", "usememo", "usecallback",
    "react", "intersection observer", "virtual scrolling", "windowing", "dom recycling",
    # DevOps & Cloud
    "kubernetes", "k8s", "docker", "blue-green", "canary", "canary deployment", "ingress",
    "service mesh", "istio", "envoy", "prometheus", "grafana", "slo", "sla", "sli", "error budget",
    "rollback", "ci/cd", "pipeline", "iac", "terraform", "helm", "autoscaling", "hpa",
    # Data Science & ML
    "imbalance", "class imbalance", "smote", "precision", "recall", "f1", "f1-score", "roc-auc",
    "pr-auc", "confusion matrix", "data leakage", "feature store", "point-in-time", "feature drift",
    "concept drift", "cross-validation", "overfitting", "underfitting", "regularization",
    "batch inference", "streaming feature", "parquet", "delta lake",
    # Behavioral & Methodology
    "star method", "situation", "task", "action", "result", "postmortem", "blameless",
    "root cause", "5 whys", "five whys", "stakeholder", "trade-off", "trade-offs", "roi",
    "technical debt", "refactoring", "kpi", "okr",
}

# Production operational edge cases
EDGE_CASE_TERMS = [
    "failure", "failover", "error", "exception", "disconnect", "retry", "fallback", "timeout",
    "offline", "recovery", "latency", "scale", "concurrency", "conflict", "security", "bottleneck",
    "edge case", "boundary", "rollback", "stampede", "drift", "leakage", "exhaustion", "drop",
    "thundering herd", "partition", "split-brain",
]

# Concrete tools and technologies
CONCRETE_TOOLS = [
    "redis", "kafka", "rabbitmq", "postgresql", "postgres", "mysql", "mongodb", "elasticsearch",
    "s3", "dynamodb", "docker", "kubernetes", "istio", "nginx", "traefik", "prometheus", "grafana",
    "react", "vue", "angular", "typescript", "python", "fastapi", "django", "aws", "gcp", "azure",
    "yjs", "automerge", "sqlite", "celery", "flink", "spark", "grpc", "axe-core", "resilience4j",
    "polly", "memcached", "sendgrid", "twilio", "apns", "fcm",
]


def extract_sentences(text: str) -> List[str]:
    """Split text into clean, non-empty sentences."""
    raw_sentences = re.split(r"(?<=[.!?])\s+", text.strip())
    sentences = [s.strip() for s in raw_sentences if len(s.strip()) > 5]
    return sentences if sentences else [text.strip()]


def find_quote_evidence(sentences: List[str], keywords: List[str], max_quotes: int = 2) -> List[str]:
    """Find verbatim sentences from response that contain target keywords."""
    matched_quotes = []
    lower_kws = [k.lower() for k in keywords]
    for sentence in sentences:
        s_lower = sentence.lower()
        if any(kw in s_lower for kw in lower_kws):
            # Clean up whitespace and limit length
            clean_s = " ".join(sentence.split())
            if len(clean_s) > 160:
                clean_s = clean_s[:157] + "..."
            if clean_s not in matched_quotes:
                matched_quotes.append(clean_s)
                if len(matched_quotes) >= max_quotes:
                    break
    return matched_quotes


def evaluate_relevance(
    question_text: str,
    user_response: str,
    role: str,
    competency: str,
    sentences: List[str],
) -> DimensionScore:
    """Evaluate whether candidate directly addresses prompt requirements (0-20)."""
    # Extract core question keywords
    raw_q_words = re.findall(r"\b[a-zA-Z]{3,}\b", question_text.lower())
    q_keywords = [w for w in raw_q_words if w not in STOPWORDS]
    unique_q_keywords = list(set(q_keywords))

    resp_lower = user_response.lower()
    matched_prompt_terms = [w for w in unique_q_keywords if w in resp_lower]

    word_count = len(user_response.split())

    # Scoring heuristic
    # Overlap fraction: up to 10 points
    target_terms_count = max(1, min(10, len(unique_q_keywords)))
    overlap_ratio = min(1.0, len(matched_prompt_terms) / target_terms_count)
    overlap_pts = overlap_ratio * 10.0

    # Response depth & elaboration: up to 10 points
    # < 30 words: low (2-4), 30-100 words: moderate (4-8), >= 100 words: full (8-10)
    if word_count < 30:
        depth_pts = min(4.0, (word_count / 30.0) * 4.0)
    elif word_count < 100:
        depth_pts = 4.0 + ((word_count - 30) / 70.0) * 4.0
    else:
        depth_pts = min(10.0, 8.0 + min(2.0, (word_count - 100) / 100.0 * 2.0))

    score = round(max(0.0, min(20.0, overlap_pts + depth_pts)), 1)

    # Extract positive evidence
    evidence = find_quote_evidence(sentences, matched_prompt_terms or unique_q_keywords[:3])
    if not evidence and sentences:
        evidence = [sentences[0][:140]]

    # Feedback message
    if score >= 16.0:
        feedback = "Exceptional relevance; directly addresses the core constraints, architecture, and prompt objectives."
    elif score >= 12.0:
        feedback = "Good prompt alignment; addresses primary requirements but could elaborate further on specific constraints."
    elif score >= 8.0:
        feedback = "Partially relevant; touches on the topic but omits explicit constraints highlighted in the question."
    else:
        feedback = "Low prompt relevance or very brief answer; ensure you address the exact technical problem stated."

    return DimensionScore(
        dimension="relevance",
        label=DIMENSION_LABELS["relevance"],
        score=score,
        max_score=20.0,
        feedback=feedback,
        positive_evidence=evidence,
    )


def evaluate_technical_correctness(
    user_response: str,
    sentences: List[str],
) -> DimensionScore:
    """Evaluate technical domain precision, valid terminology, and architecture accuracy (0-20)."""
    resp_lower = user_response.lower()

    # Find verified technical terms
    found_terms = [t for t in TECHNICAL_TERMS if t in resp_lower]
    unique_terms_count = len(found_terms)

    # Score calculation
    # Term density: 0 terms -> 5.0 base; 1-2 terms -> 8-11; 3-5 terms -> 12-15; 6+ terms -> 16-20
    if unique_terms_count == 0:
        base_score = 6.0
    elif unique_terms_count <= 2:
        base_score = 8.0 + (unique_terms_count * 2.0)
    elif unique_terms_count <= 5:
        base_score = 12.0 + ((unique_terms_count - 2) * 1.2)
    else:
        base_score = 16.0 + min(4.0, (unique_terms_count - 5) * 0.8)

    score = round(max(0.0, min(20.0, base_score)), 1)

    # Extract evidence containing technical terms
    evidence = find_quote_evidence(sentences, found_terms)
    if not evidence and sentences:
        evidence = [sentences[0][:140]]

    if score >= 16.0:
        feedback = (
            f"High technical precision citing {unique_terms_count} domain concepts with accurate contextual usage."
        )
    elif score >= 12.0:
        feedback = f"Technically sound ({unique_terms_count} concepts identified); clear articulation of underlying concepts."
    elif score >= 8.0:
        feedback = "Basic technical foundation; enhance credibility by referencing formal protocols, data structures, and algorithms."
    else:
        feedback = "Limited technical specificity; incorporate industry-standard technologies and exact architectural patterns."

    return DimensionScore(
        dimension="technical_correctness",
        label=DIMENSION_LABELS["technical_correctness"],
        score=score,
        max_score=20.0,
        feedback=feedback,
        positive_evidence=evidence,
    )


def evaluate_completeness(
    user_response: str,
    key_concepts: List[str],
    sentences: List[str],
) -> Tuple[DimensionScore, List[str], List[str]]:
    """Evaluate key concept coverage and handling of operational edge cases (0-20)."""
    resp_lower = user_response.lower()

    covered = []
    missed = []
    for concept in key_concepts:
        # Check if full concept or primary tokens appear
        c_lower = concept.lower()
        # Clean special chars from concept
        c_clean = re.sub(r"[\(\)\/]", " ", c_lower)
        tokens = [t.strip() for t in c_clean.split() if len(t.strip()) > 2 and t.strip() not in STOPWORDS]

        if c_lower in resp_lower or (tokens and all(tok in resp_lower for tok in tokens)):
            covered.append(concept)
        elif tokens and any(tok in resp_lower for tok in tokens) and len(tokens) <= 2:
            covered.append(concept)
        else:
            missed.append(concept)

    # Edge cases mentioned
    edge_cases_found = [e for e in EDGE_CASE_TERMS if e in resp_lower]

    # Concept coverage ratio: up to 14 points
    if key_concepts:
        concept_ratio = len(covered) / len(key_concepts)
    else:
        concept_ratio = 0.8
    concept_pts = concept_ratio * 14.0

    # Operational edge cases: up to 6 points
    edge_pts = min(6.0, len(edge_cases_found) * 1.5)

    score = round(max(0.0, min(20.0, concept_pts + edge_pts)), 1)

    # Evidence: quotes matching covered concepts or edge cases
    search_targets = covered + edge_cases_found
    evidence = find_quote_evidence(sentences, search_targets)
    if not evidence and sentences:
        evidence = [sentences[0][:140]]

    total_expected = len(key_concepts)
    if score >= 16.0:
        feedback = (
            f"Comprehensive answer covering {len(covered)}/{total_expected} core concepts and "
            f"proactively addressing {len(edge_cases_found)} production edge cases."
        )
    elif score >= 11.0:
        feedback = (
            f"Solid coverage ({len(covered)}/{total_expected} core concepts); "
            "expanding on failure recovery and concurrency limits would complete the response."
        )
    else:
        feedback = (
            f"Incomplete scope; missed key concepts: {', '.join(missed[:3]) if missed else 'core requirements'}. "
            "Ensure operational edge cases are addressed."
        )

    score_obj = DimensionScore(
        dimension="completeness",
        label=DIMENSION_LABELS["completeness"],
        score=score,
        max_score=20.0,
        feedback=feedback,
        positive_evidence=evidence,
    )
    return score_obj, covered, missed


def evaluate_structure(
    user_response: str,
    competency: str,
    sentences: List[str],
) -> DimensionScore:
    """Evaluate structural organization, logical transitions, and methodology (0-20)."""
    resp_lower = user_response.lower()

    # 1. Paragraph breaks
    paragraphs = [p.strip() for p in re.split(r"\n+", user_response) if len(p.strip()) > 10]
    has_multiple_paragraphs = len(paragraphs) >= 2

    # 2. Numbered or bullet lists
    has_lists = bool(re.search(r"(\b\d+[\.\)]\s+|^[\-\*\•]\s+)", user_response, re.MULTILINE))

    # 3. Structural section headings or transition markers
    transitions = [
        "first", "firstly", "second", "secondly", "third", "finally", "furthermore",
        "moreover", "in addition", "additionally", "in terms of", "in conclusion",
        "to summarize", "specifically", "for storage", "on the frontend", "on the backend",
        "architecture:", "components:", "trade-offs:", "tradeoffs:",
    ]
    transition_count = sum(1 for t in transitions if t in resp_lower)

    # 4. STAR method indicators (for behavioral competency)
    is_behavioral = "behavioral" in competency.lower() or "leadership" in competency.lower()
    star_markers = ["situation", "task", "action", "result", "outcome", "impact"]
    star_count = sum(1 for m in star_markers if m in resp_lower)

    # Base points for sentence count
    base = 6.0 if len(sentences) >= 3 else 4.0

    # Paragraph bonus
    para_pts = 4.0 if has_multiple_paragraphs else 0.0

    # List or transition bonus
    list_pts = 4.0 if has_lists else min(3.0, transition_count * 1.0)

    # Flow / elaboration bonus
    flow_pts = min(6.0, transition_count * 1.5)

    if is_behavioral and star_count >= 3:
        flow_pts = max(flow_pts, 6.0)

    score = round(max(0.0, min(20.0, base + para_pts + list_pts + flow_pts)), 1)

    evidence = find_quote_evidence(sentences, transitions + star_markers)
    if not evidence and sentences:
        evidence = [sentences[0][:140]]

    if score >= 16.0:
        feedback = "Exemplary structure; logical progression, clear sectioning, and smooth transitions between components."
    elif score >= 12.0:
        feedback = "Well-structured flow; clear logical sequence. Using explicit bullet points or numbered steps will further clarify trade-offs."
    elif score >= 8.0:
        feedback = "Readable but somewhat uniform; break up long paragraphs with bulleted lists and clear architectural headers."
    else:
        feedback = "Unstructured answer; organize your response into distinct sections or utilize the STAR framework."

    return DimensionScore(
        dimension="structure",
        label=DIMENSION_LABELS["structure"],
        score=score,
        max_score=20.0,
        feedback=feedback,
        positive_evidence=evidence,
    )


def evaluate_use_of_examples(
    user_response: str,
    sentences: List[str],
) -> DimensionScore:
    """Evaluate inclusion of concrete technologies, quantitative SLAs, and code/scenario citations (0-20)."""
    resp_lower = user_response.lower()

    # 1. Concrete named software/tools
    tools_cited = [t for t in CONCRETE_TOOLS if t in resp_lower]
    tools_count = len(tools_cited)

    # 2. Quantitative measurements and metrics
    # e.g., 50ms, 99.9%, 10,000, 30 seconds, 100 million
    metrics_matches = re.findall(
        r"\b\d+(?:\.\d+)?\s*(?:ms|milliseconds?|seconds?|mins?|minutes?|hours?|%|percent|rps|qps|mb|gb|tb|rows|million|users?|events?)\b",
        resp_lower,
    )
    metrics_count = len(metrics_matches)

    # 3. Code, syntax, or API signatures
    code_matches = re.findall(
        r"(?:def\s+\w+|class\s+\w+|\bget\(|\bset\(|SELECT|INSERT|UPDATE|DELETE|HTTP\s+\d{3}|\b200\b|\b429\b|\b500\b|JSON|API)",
        user_response,
    )
    code_count = len(code_matches)

    # 4. Illustrative keywords
    illustrative_cues = ["for example", "such as", "specifically", "in my experience", "in a previous project", "for instance", "to illustrate"]
    cue_count = sum(1 for cue in illustrative_cues if cue in resp_lower)

    # Scoring weights
    tool_pts = min(7.0, tools_count * 2.0)
    metric_pts = min(5.0, metrics_count * 2.5)
    code_pts = min(4.0, code_count * 2.0)
    cue_pts = min(4.0, cue_count * 2.0)

    # Minimum base for substantive response
    base_pts = 3.0 if len(user_response.split()) >= 40 else 1.0

    score = round(max(0.0, min(20.0, base_pts + tool_pts + metric_pts + code_pts + cue_pts)), 1)

    evidence_targets = tools_cited + metrics_matches + illustrative_cues
    evidence = find_quote_evidence(sentences, evidence_targets)
    if not evidence and sentences:
        evidence = [sentences[0][:140]]

    if score >= 16.0:
        feedback = (
            f"Vivid grounding with {tools_count} named technologies, {metrics_count} quantitative metrics, "
            "and concrete real-world implementation examples."
        )
    elif score >= 11.0:
        feedback = (
            f"Concrete choices ({', '.join(tools_cited[:3]) if tools_cited else 'named systems'}); "
            "adding quantitative SLAs (e.g. latency, throughput, uptime targets) will elevate technical authority."
        )
    elif score >= 7.0:
        feedback = "Some illustrative examples; substantiate your claims by specifying production tools and measurable performance targets."
    else:
        feedback = "Abstract answer lacking real-world grounding; name specific databases, libraries, or architectural implementations."

    return DimensionScore(
        dimension="use_of_examples",
        label=DIMENSION_LABELS["use_of_examples"],
        score=score,
        max_score=20.0,
        feedback=feedback,
        positive_evidence=evidence,
    )


def evaluate_response(
    question_text: str,
    user_response: str,
    role: str = "Full-Stack Engineer",
    competency: str = "System Design",
    key_concepts: Optional[List[str]] = None,
) -> RubricFeedback:
    """Evaluate candidate's typed response across 5 standard technical interview dimensions."""
    sentences = extract_sentences(user_response)
    expected_concepts = key_concepts or []

    # 1. Relevance
    dim_relevance = evaluate_relevance(question_text, user_response, role, competency, sentences)

    # 2. Technical Correctness
    dim_correctness = evaluate_technical_correctness(user_response, sentences)

    # 3. Completeness
    dim_completeness, covered_concepts, missed_concepts = evaluate_completeness(
        user_response, expected_concepts, sentences
    )

    # 4. Structure
    dim_structure = evaluate_structure(user_response, competency, sentences)

    # 5. Use of Examples
    dim_examples = evaluate_use_of_examples(user_response, sentences)

    dimension_scores = {
        "relevance": dim_relevance,
        "technical_correctness": dim_correctness,
        "completeness": dim_completeness,
        "structure": dim_structure,
        "use_of_examples": dim_examples,
    }

    # Total score bounded between 0.0 and 100.0
    total_score = round(sum(d.score for d in dimension_scores.values()), 1)
    total_score = max(0.0, min(100.0, total_score))

    # Positive Highlights (collect unique evidence snippets from top dimensions)
    highlights: List[str] = []
    # Sort dimensions by score descending
    sorted_dims = sorted(dimension_scores.values(), key=lambda d: d.score, reverse=True)
    for dim in sorted_dims:
        for ev in dim.positive_evidence:
            if ev and ev not in highlights and len(highlights) < 3:
                highlights.append(ev)

    # Actionable Improvements (targeted feedback on lower-scoring areas)
    improvements: List[str] = []
    if missed_concepts:
        improvements.append(f"Incorporate missing core concepts: {', '.join(missed_concepts[:3])}.")
    if dim_examples.score < 14.0:
        improvements.append("Cite concrete technologies and quantitative SLA metrics (e.g. sub-50ms latency, p99 percentiles).")
    if dim_structure.score < 14.0:
        improvements.append("Organize your response using structured paragraph blocks, numbered steps, or explicit trade-off headings.")
    if dim_completeness.score < 14.0:
        improvements.append("Proactively address failure modes, network disconnects, and operational edge cases.")
    if not improvements:
        improvements.append("Maintain this high standard; practice delivering this structured articulation concisely under interview time constraints.")

    # Executive Summary
    if total_score >= 85.0:
        summary = "Exemplary technical response demonstrating thorough domain mastery, clear structure, and concrete real-world grounding."
    elif total_score >= 70.0:
        summary = "Strong technical response with solid conceptual foundation; minor opportunities to sharpen quantitative metrics and edge-case handling."
    elif total_score >= 50.0:
        summary = "Good foundational response; focus on incorporating concrete implementation examples, named tools, and structured organization."
    else:
        summary = "Initial response needs expansion; ensure you directly address all prompt constraints using formal technical terminology."

    return RubricFeedback(
        rubric_version=RUBRIC_VERSION,
        total_score=total_score,
        dimension_scores=dimension_scores,
        key_concepts_covered=covered_concepts,
        key_concepts_missed=missed_concepts,
        positive_highlights=highlights,
        actionable_improvements=improvements,
        summary=summary,
    )

