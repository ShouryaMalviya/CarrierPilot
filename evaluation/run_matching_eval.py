"""Deterministic Information Retrieval (IR) evaluation harness for job matching.

Evaluates lexical and hybrid matching algorithms against a frozen benchmark dataset
using standard ranking and recommendation metrics:
- Mean Reciprocal Rank (MRR)
- Recall@K (K=1, 3, 5)
- Normalized Discounted Cumulative Gain (nDCG@K, K=3, 5)
- Precision@K (K=1, 3)

No random seeds, network access, or paid APIs required.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

# Ensure backend package can be imported
PROJECT_ROOT = Path(__file__).resolve().parent.parent
BACKEND_DIR = PROJECT_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.services.matching_service import calculate_lexical_match  # noqa: E402


# ==============================================================================
# Metric Computation Core Functions
# ==============================================================================

def compute_dcg_at_k(relevances: List[int], k: int) -> float:
    """Compute Discounted Cumulative Gain up to position k.

    Uses the standard exponential formulation:
    DCG@K = sum_{i=1}^{min(k, len(relevances))} (2^{rel_i} - 1) / log2(i + 1)
    """
    if k <= 0 or not relevances:
        return 0.0

    dcg = 0.0
    for i, rel in enumerate(relevances[:k], start=1):
        if rel > 0:
            dcg += (math.pow(2, rel) - 1.0) / math.log2(i + 1)
    return dcg


def compute_ndcg_at_k(
    retrieved_ids: List[str],
    ground_truth: Dict[str, int],
    k: int,
) -> float:
    """Compute Normalized Discounted Cumulative Gain at rank k (nDCG@K).

    Args:
        retrieved_ids: Ordered list of retrieved document/job IDs.
        ground_truth: Mapping of document/job ID to integer relevance grade (e.g. 0 to 3).
        k: Truncation cutoff rank.

    Returns:
        float in [0.0, 1.0], rounded to 4 decimal places.
    """
    if k <= 0 or not retrieved_ids or not ground_truth:
        return 0.0

    # Actual DCG from retrieved ranking
    actual_relevances = [ground_truth.get(doc_id, 0) for doc_id in retrieved_ids[:k]]
    actual_dcg = compute_dcg_at_k(actual_relevances, k)

    # Ideal DCG from descending sorted ground truth
    ideal_relevances = sorted(ground_truth.values(), reverse=True)[:k]
    ideal_dcg = compute_dcg_at_k(ideal_relevances, k)

    if ideal_dcg <= 0.0:
        return 0.0

    return round(min(1.0, actual_dcg / ideal_dcg), 4)


def compute_recall_at_k(
    retrieved_ids: List[str],
    ground_truth: Dict[str, int],
    k: int,
    threshold: int = 2,
) -> float:
    """Compute Recall@K against relevant ground truth items.

    Args:
        retrieved_ids: Ordered list of retrieved document/job IDs.
        ground_truth: Mapping of document/job ID to relevance grade.
        k: Truncation cutoff rank.
        threshold: Minimum relevance grade to consider an item relevant (default: 2).

    Returns:
        float in [0.0, 1.0], rounded to 4 decimal places.
    """
    if k <= 0:
        return 0.0

    relevant_set = {doc_id for doc_id, rel in ground_truth.items() if rel >= threshold}
    if not relevant_set:
        # Vacuously all relevant items retrieved
        return 1.0

    retrieved_top_k = set(retrieved_ids[:k])
    matched = len(retrieved_top_k.intersection(relevant_set))
    return round(matched / len(relevant_set), 4)


def compute_precision_at_k(
    retrieved_ids: List[str],
    ground_truth: Dict[str, int],
    k: int,
    threshold: int = 2,
) -> float:
    """Compute Precision@K against relevant ground truth items.

    Args:
        retrieved_ids: Ordered list of retrieved document/job IDs.
        ground_truth: Mapping of document/job ID to relevance grade.
        k: Truncation cutoff rank.
        threshold: Minimum relevance grade to consider an item relevant (default: 2).

    Returns:
        float in [0.0, 1.0], rounded to 4 decimal places.
    """
    if k <= 0 or not retrieved_ids:
        return 0.0

    top_k = retrieved_ids[:k]
    actual_k = len(top_k)
    if actual_k == 0:
        return 0.0

    relevant_count = sum(1 for doc_id in top_k if ground_truth.get(doc_id, 0) >= threshold)
    return round(relevant_count / actual_k, 4)


def compute_mrr(
    retrieved_ids: List[str],
    ground_truth: Dict[str, int],
    threshold: int = 2,
) -> float:
    """Compute Reciprocal Rank (RR) for a single query.

    Args:
        retrieved_ids: Ordered list of retrieved document/job IDs.
        ground_truth: Mapping of document/job ID to relevance grade.
        threshold: Minimum relevance grade to consider an item relevant (default: 2).

    Returns:
        float in [0.0, 1.0], rounded to 4 decimal places.
    """
    for rank, doc_id in enumerate(retrieved_ids, start=1):
        if ground_truth.get(doc_id, 0) >= threshold:
            return round(1.0 / rank, 4)
    return 0.0


# ==============================================================================
# Benchmark Evaluation Pipeline
# ==============================================================================

def evaluate_candidate_matching(
    candidate: Dict[str, Any],
    jobs: List[Dict[str, Any]],
    use_semantic: bool = False,
) -> Dict[str, Any]:
    """Score all jobs for a single candidate, rank them, and compute IR metrics."""
    cand_text = candidate.get("resume_text", "")
    cand_skills = set(candidate.get("skills", []))
    ground_truth = candidate.get("ground_truth_relevance", {})

    scored_jobs = []
    for job in jobs:
        job_id = job["id"]
        job_text = job.get("description", "")
        req_skills = set(job.get("required_skills", []))
        pref_skills = set(job.get("preferred_skills", []))

        scores, gap = calculate_lexical_match(
            resume_text=cand_text,
            resume_skills=cand_skills,
            job_text=job_text,
            required_skills=req_skills,
            preferred_skills=pref_skills,
            use_semantic=use_semantic,
        )

        scored_jobs.append({
            "job_id": job_id,
            "job_title": job.get("title", ""),
            "overall_score": scores.overall_score,
            "required_coverage": scores.required_coverage,
            "preferred_coverage": scores.preferred_coverage,
            "tfidf_similarity": scores.tfidf_similarity,
            "semantic_similarity": scores.semantic_similarity,
            "ground_truth_relevance": ground_truth.get(job_id, 0),
            "matched_required": gap.matched_required,
            "missing_required": gap.missing_required,
        })

    # Sort descending by overall_score, tie-breaking by required_coverage and tfidf_similarity
    scored_jobs.sort(
        key=lambda item: (
            item["overall_score"],
            item["required_coverage"],
            item["tfidf_similarity"],
        ),
        reverse=True,
    )

    ranked_job_ids = [item["job_id"] for item in scored_jobs]

    # Compute metrics
    metrics = {
        "mrr": compute_mrr(ranked_job_ids, ground_truth, threshold=2),
        "recall_at_1": compute_recall_at_k(ranked_job_ids, ground_truth, k=1, threshold=2),
        "recall_at_3": compute_recall_at_k(ranked_job_ids, ground_truth, k=3, threshold=2),
        "recall_at_5": compute_recall_at_k(ranked_job_ids, ground_truth, k=5, threshold=2),
        "precision_at_1": compute_precision_at_k(ranked_job_ids, ground_truth, k=1, threshold=2),
        "precision_at_3": compute_precision_at_k(ranked_job_ids, ground_truth, k=3, threshold=2),
        "ndcg_at_3": compute_ndcg_at_k(ranked_job_ids, ground_truth, k=3),
        "ndcg_at_5": compute_ndcg_at_k(ranked_job_ids, ground_truth, k=5),
    }

    return {
        "candidate_id": candidate.get("id"),
        "candidate_name": candidate.get("name"),
        "target_role": candidate.get("target_role"),
        "ranked_jobs": scored_jobs,
        "metrics": metrics,
    }


def run_matching_evaluation(
    benchmark_path: Optional[str] = None,
    output_path: Optional[str] = None,
    use_semantic: bool = False,
) -> Dict[str, Any]:
    """Execute the full evaluation benchmark across all candidate queries."""
    if benchmark_path is None:
        benchmark_path = str(PROJECT_ROOT / "evaluation" / "data" / "matching_benchmark.json")

    with open(benchmark_path, "r", encoding="utf-8") as f:
        benchmark_data = json.load(f)

    jobs = benchmark_data.get("jobs", [])
    candidates = benchmark_data.get("candidates", [])

    candidate_results = []
    for cand in candidates:
        res = evaluate_candidate_matching(cand, jobs, use_semantic=use_semantic)
        candidate_results.append(res)

    num_candidates = len(candidates)
    if num_candidates == 0:
        macro_metrics = {
            "mean_mrr": 0.0,
            "mean_recall_at_1": 0.0,
            "mean_recall_at_3": 0.0,
            "mean_recall_at_5": 0.0,
            "mean_precision_at_1": 0.0,
            "mean_precision_at_3": 0.0,
            "mean_ndcg_at_3": 0.0,
            "mean_ndcg_at_5": 0.0,
        }
    else:
        macro_metrics = {
            "mean_mrr": round(sum(c["metrics"]["mrr"] for c in candidate_results) / num_candidates, 4),
            "mean_recall_at_1": round(sum(c["metrics"]["recall_at_1"] for c in candidate_results) / num_candidates, 4),
            "mean_recall_at_3": round(sum(c["metrics"]["recall_at_3"] for c in candidate_results) / num_candidates, 4),
            "mean_recall_at_5": round(sum(c["metrics"]["recall_at_5"] for c in candidate_results) / num_candidates, 4),
            "mean_precision_at_1": round(sum(c["metrics"]["precision_at_1"] for c in candidate_results) / num_candidates, 4),
            "mean_precision_at_3": round(sum(c["metrics"]["precision_at_3"] for c in candidate_results) / num_candidates, 4),
            "mean_ndcg_at_3": round(sum(c["metrics"]["ndcg_at_3"] for c in candidate_results) / num_candidates, 4),
            "mean_ndcg_at_5": round(sum(c["metrics"]["ndcg_at_5"] for c in candidate_results) / num_candidates, 4),
        }

    evaluation_report = {
        "benchmark_version": benchmark_data.get("version", "1.0.0"),
        "benchmark_description": benchmark_data.get("description", ""),
        "total_jobs": len(jobs),
        "total_candidates": num_candidates,
        "mode": "hybrid/semantic" if use_semantic else "lexical_baseline",
        "macro_metrics": macro_metrics,
        "candidate_results": candidate_results,
    }

    if output_path:
        out_file = Path(output_path)
        out_file.parent.mkdir(parents=True, exist_ok=True)
        with open(out_file, "w", encoding="utf-8") as f:
            json.dump(evaluation_report, f, indent=2)

    return evaluation_report


def print_evaluation_summary(report: Dict[str, Any]) -> None:
    """Print clean terminal tables summarizing benchmark evaluation results."""
    macro = report["macro_metrics"]
    print("=" * 76)
    print(f"CAREERPILOT PLACEMENT MATCHING BENCHMARK REPORT (Mode: {report['mode']})")
    print(f"Benchmark: {report['benchmark_description']}")
    print(f"Evaluated: {report['total_candidates']} candidates against {report['total_jobs']} job roles")
    print("-" * 76)
    print(f"{'Metric':<28} | {'Score':<10} | {'Interpretation'}")
    print("-" * 76)
    print(f"{'Mean Reciprocal Rank (MRR)':<28} | {macro['mean_mrr']:<10.4f} | First relevant job rank quality")
    print(f"{'Mean Recall@1':<28} | {macro['mean_recall_at_1']:<10.4f} | Relevant jobs captured at rank 1")
    print(f"{'Mean Recall@3':<28} | {macro['mean_recall_at_3']:<10.4f} | Relevant jobs captured in top 3")
    print(f"{'Mean Recall@5':<28} | {macro['mean_recall_at_5']:<10.4f} | Relevant jobs captured in top 5")
    print(f"{'Mean Precision@1':<28} | {macro['mean_precision_at_1']:<10.4f} | Top-1 accuracy")
    print(f"{'Mean Precision@3':<28} | {macro['mean_precision_at_3']:<10.4f} | Top-3 density")
    print(f"{'Mean nDCG@3':<28} | {macro['mean_ndcg_at_3']:<10.4f} | Graded ranking quality at top 3")
    print(f"{'Mean nDCG@5':<28} | {macro['mean_ndcg_at_5']:<10.4f} | Graded ranking quality across all 5")
    print("=" * 76)
    print("\nPer-Candidate Breakdown:")
    print("-" * 76)
    for c in report["candidate_results"]:
        m = c["metrics"]
        top_job = c["ranked_jobs"][0]
        print(f"Candidate: {c['candidate_name']:<18} Target: {c['target_role']}")
        print(f"  Top Match: {top_job['job_title']:<28} (Score: {top_job['overall_score']:5.1f}, GT: {top_job['ground_truth_relevance']})")
        print(f"  MRR: {m['mrr']:.2f} | Recall@3: {m['recall_at_3']:.2f} | nDCG@3: {m['ndcg_at_3']:.2f} | nDCG@5: {m['ndcg_at_5']:.2f}")
        print("-" * 76)


def main() -> None:
    parser = argparse.ArgumentParser(description="CareerPilot Job Matching IR Evaluation")
    parser.add_argument("--benchmark", type=str, default=None, help="Path to benchmark JSON")
    parser.add_argument("--output", type=str, default="evaluation/results/matching_metrics.json", help="Path to write output JSON")
    parser.add_argument("--semantic", action="store_true", help="Enable neural semantic matching adapter")
    args = parser.parse_args()

    report = run_matching_evaluation(
        benchmark_path=args.benchmark,
        output_path=args.output,
        use_semantic=args.semantic,
    )
    print_evaluation_summary(report)


if __name__ == "__main__":
    main()

