# Model Card: Exponential Decay Adaptive Mastery Engine

## Model Details
- **Model Name**: CareerPilot Recency-Decay Mastery Engine (v1.0.0)
- **Model Type**: Transparent Exponential Decay Recency-Weighted Information Tracker.
- **Mathematical Formula**:
  $$M(T) = 100 \times \frac{\sum_{i=1}^n \gamma^{n-i} \cdot c_i \cdot d_i}{\sum_{i=1}^n \gamma^{n-i} \cdot d_i}$$
  - $\gamma = 0.85$ (Exponential decay factor)
  - $c_i \in \{0.0, 1.0\}$ (Attempt correctness)
  - $d_i \in \{0.8 \text{ [Easy]}, 1.0 \text{ [Medium]}, 1.2 \text{ [Hard]}\}$ (Difficulty multiplier)
  - $n \le 10$ (Sliding evaluation window)
- **License**: Academic / Educational Open Source (MIT)

## Intended Use
- **Primary Use Case**: Diagnostic student skill evaluation, tracking adaptive learning progression across practice sessions, and identifying topics needing targeted remediation.
- **Explainability Feature**: Accessible audit endpoint (`GET /api/v1/practice/mastery/{topic}`) disclosing exact weights and formulas for complete transparency.
- **Out-of-Scope / Prohibited Uses**:
  - High-stakes summative examination grading.
  - Psychometric profiling or cognitive speed inference.

## Transparency & Reason Codes
The engine classifies mastery into explainable pedagogical tiers:
- **Mastered** ($\ge 85\%$): `HIGH_ACCURACY`, `RECENT_IMPROVEMENT`
- **Proficient** ($70\% - 84\%$): `TOPIC_PROFICIENT`, `CONSISTENT`
- **Developing** ($50\% - 69\%$): `DEVELOPING`, `VARIABLE_ACCURACY`
- **Needs Practice** ($< 50\%$): `NEEDS_PRACTICE`, `STRUGGLING`

## Ethical Considerations & Limitations
- **Objective MCQ Focus**: Measures conceptual recall and code syntax comprehension; does not evaluate full software design synthesis or teamwork.
- **Deterministic Transparency**: Every student can inspect the exact mathematical contributions of each prior attempt without proprietary black-box calculations.

