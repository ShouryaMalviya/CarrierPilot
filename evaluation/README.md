# CareerPilot AI — Evaluation Protocol & Benchmark Datasets

## Overview
Evaluation harness, frozen synthetic benchmark datasets, and reproducible metrics for offline model and heuristic validation.

## Principles
1. **Frozen Datasets**: Benchmark data is version-controlled and never modified ad-hoc.
2. **Deterministic Metrics**: Evaluates ranking using standard Information Retrieval metrics:
   - **Recall@K**
   - **MRR (Mean Reciprocal Rank)**
   - **nDCG@K (Normalized Discounted Cumulative Gain)**
3. **Zero Fabricated Results**: All reported tables, graphs, and metrics must be output from automated scripts running against frozen test splits.

