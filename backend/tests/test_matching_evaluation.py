"""Unit and integration tests for IR matching evaluation metrics and benchmark harness."""

import json
import math
import os
import sys
from pathlib import Path
import pytest

# Ensure evaluation directory is importable
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
EVALUATION_DIR = PROJECT_ROOT / "evaluation"
if str(EVALUATION_DIR) not in sys.path:
    sys.path.insert(0, str(EVALUATION_DIR))

from run_matching_eval import (
    compute_dcg_at_k,
    compute_ndcg_at_k,
    compute_recall_at_k,
    compute_precision_at_k,
    compute_mrr,
    evaluate_candidate_matching,
    run_matching_evaluation,
)


# ==============================================================================
# Metric Math Unit Tests
# ==============================================================================

class TestEvaluationMetricMath:
    """Validate mathematical correctness of deterministic ranking evaluation metrics."""

    def test_dcg_at_k_empty_and_zero(self):
        """DCG with empty or zero relevances must return 0.0."""
        assert compute_dcg_at_k([], 5) == 0.0
        assert compute_dcg_at_k([0, 0, 0], 3) == 0.0
        assert compute_dcg_at_k([3, 2, 1], 0) == 0.0
        assert compute_dcg_at_k([3, 2, 1], -1) == 0.0

    def test_dcg_at_k_known_values(self):
        """Verify DCG calculation: (2^rel - 1) / log2(i + 1)."""
        # Rank 1: rel=3 -> (8 - 1) / log2(2) = 7.0 / 1.0 = 7.0
        assert pytest.approx(compute_dcg_at_k([3], 1), 0.001) == 7.0

        # Rank 1: rel=3, Rank 2: rel=2 -> 7.0 + (4 - 1) / log2(3) = 7.0 + 3.0 / 1.58496 = 8.8928
        expected = 7.0 + 3.0 / math.log2(3)
        assert pytest.approx(compute_dcg_at_k([3, 2], 2), 0.001) == expected

    def test_ndcg_at_k_perfect_ranking(self):
        """When retrieved ordering matches ideal ordering, nDCG@K must be 1.0."""
        retrieved = ["job_a", "job_b", "job_c"]
        ground_truth = {"job_a": 3, "job_b": 2, "job_c": 1}

        ndcg = compute_ndcg_at_k(retrieved, ground_truth, k=3)
        assert ndcg == 1.0

    def test_ndcg_at_k_inverted_ranking(self):
        """Inverted ranking should have lower nDCG than 1.0."""
        retrieved = ["job_c", "job_b", "job_a"]
        ground_truth = {"job_a": 3, "job_b": 2, "job_c": 1}

        ndcg = compute_ndcg_at_k(retrieved, ground_truth, k=3)
        assert 0.0 < ndcg < 1.0

    def test_ndcg_at_k_zero_relevance(self):
        """When all ground truth relevances are zero, nDCG@K returns 0.0."""
        retrieved = ["job_a", "job_b"]
        ground_truth = {"job_a": 0, "job_b": 0}
        assert compute_ndcg_at_k(retrieved, ground_truth, k=2) == 0.0

    def test_recall_at_k(self):
        """Recall@K tests proportion of relevant items retrieved in top K."""
        ground_truth = {"job_1": 3, "job_2": 2, "job_3": 0}
        # Relevant set: {job_1, job_2} (size 2)

        # Retrieve both in top 2
        assert compute_recall_at_k(["job_1", "job_2", "job_3"], ground_truth, k=2) == 1.0

        # Retrieve 1 out of 2 in top 1
        assert compute_recall_at_k(["job_1", "job_2", "job_3"], ground_truth, k=1) == 0.5

        # Retrieve irrelevant in top 1
        assert compute_recall_at_k(["job_3", "job_1", "job_2"], ground_truth, k=1) == 0.0

        # No relevant items in ground truth -> vacuously 1.0
        assert compute_recall_at_k(["job_1"], {"job_1": 0}, k=1) == 1.0

        # Non-positive k -> 0.0
        assert compute_recall_at_k(["job_1"], ground_truth, k=0) == 0.0

    def test_precision_at_k(self):
        """Precision@K measures fraction of top K items that are relevant."""
        ground_truth = {"job_1": 3, "job_2": 2, "job_3": 0}

        # Top 1 is relevant -> 1/1 = 1.0
        assert compute_precision_at_k(["job_1", "job_3"], ground_truth, k=1) == 1.0

        # Top 2 has 1 relevant, 1 irrelevant -> 1/2 = 0.5
        assert compute_precision_at_k(["job_1", "job_3"], ground_truth, k=2) == 0.5

        # Empty retrieved -> 0.0
        assert compute_precision_at_k([], ground_truth, k=3) == 0.0
        assert compute_precision_at_k(["job_1"], ground_truth, k=0) == 0.0

    def test_mrr(self):
        """MRR measures reciprocal rank of the first relevant item."""
        ground_truth = {"job_a": 0, "job_b": 2, "job_c": 3}

        # First item is relevant (rank 1) -> 1/1 = 1.0
        assert compute_mrr(["job_b", "job_a", "job_c"], ground_truth) == 1.0

        # Second item is relevant (rank 2) -> 1/2 = 0.5
        assert compute_mrr(["job_a", "job_b", "job_c"], ground_truth) == 0.5

        # Third item is relevant (rank 3) -> 1/3 = 0.3333
        assert compute_mrr(["job_a", "job_x", "job_c"], ground_truth) == 0.3333

        # No relevant items retrieved -> 0.0
        assert compute_mrr(["job_a", "job_x"], ground_truth) == 0.0


# ==============================================================================
# Pipeline & Benchmark Integration Tests
# ==============================================================================

class TestBenchmarkHarness:
    """Validate end-to-end execution of the matching benchmark."""

    def test_evaluate_candidate_matching_structure(self):
        """Single candidate evaluation must return sorted jobs and metrics."""
        candidate = {
            "id": "cand_test",
            "name": "Test Candidate",
            "target_role": "Python Dev",
            "resume_text": "Experienced Python and FastAPI backend developer with SQL.",
            "skills": ["Python", "FastAPI", "SQL"],
            "ground_truth_relevance": {"job_1": 3, "job_2": 0},
        }
        jobs = [
            {
                "id": "job_1",
                "title": "Backend Python",
                "description": "Python, FastAPI, and SQL developer.",
                "required_skills": ["Python", "FastAPI", "SQL"],
                "preferred_skills": [],
            },
            {
                "id": "job_2",
                "title": "Frontend React",
                "description": "React and TypeScript engineer.",
                "required_skills": ["React", "TypeScript"],
                "preferred_skills": [],
            },
        ]

        result = evaluate_candidate_matching(candidate, jobs, use_semantic=False)
        assert result["candidate_id"] == "cand_test"
        assert len(result["ranked_jobs"]) == 2
        # job_1 should score significantly higher than job_2
        assert result["ranked_jobs"][0]["job_id"] == "job_1"
        assert result["ranked_jobs"][0]["overall_score"] > result["ranked_jobs"][1]["overall_score"]
        # MRR should be 1.0
        assert result["metrics"]["mrr"] == 1.0
        assert result["metrics"]["recall_at_1"] == 1.0

    def test_run_matching_evaluation_benchmark_data(self, tmp_path):
        """End-to-end benchmark execution against frozen dataset."""
        benchmark_file = PROJECT_ROOT / "evaluation" / "data" / "matching_benchmark.json"
        assert benchmark_file.exists(), f"Benchmark file missing at {benchmark_file}"

        out_file = tmp_path / "metrics_test_output.json"
        report = run_matching_evaluation(
            benchmark_path=str(benchmark_file),
            output_path=str(out_file),
            use_semantic=False,
        )

        # Validate top-level metadata
        assert report["benchmark_version"] == "1.0.0"
        assert report["total_candidates"] == 5
        assert report["total_jobs"] == 5
        assert report["mode"] == "lexical_baseline"

        # Validate macro metrics exceed required baseline quality thresholds
        macro = report["macro_metrics"]
        assert macro["mean_mrr"] >= 0.90, f"MRR too low: {macro['mean_mrr']}"
        assert macro["mean_recall_at_3"] >= 0.85, f"Recall@3 too low: {macro['mean_recall_at_3']}"
        assert macro["mean_ndcg_at_3"] >= 0.90, f"nDCG@3 too low: {macro['mean_ndcg_at_3']}"
        assert macro["mean_precision_at_1"] >= 0.80, f"Precision@1 too low: {macro['mean_precision_at_1']}"

        # Validate that JSON report was serialized and can be read back
        assert out_file.exists()
        with open(out_file, "r", encoding="utf-8") as f:
            saved_report = json.load(f)
        assert saved_report["macro_metrics"]["mean_mrr"] == macro["mean_mrr"]
