# Model Card: Rubric-Based Mock Interview Evaluator

## Model Details
- **Model Name**: CareerPilot 5-Dimension Interview Rubric Engine (v1.0.0)
- **Model Type**: Structured Technical Articulation Coaching Evaluator with Verbatim Quote Extraction.
- **Evaluation Dimensions** (20 Points Each, 100 Total):
  1. **Relevance to Prompt [0–20]**: Alignment with technical prompt constraints and problem scope.
  2. **Technical Correctness [0–20]**: Accurate utilization of formal protocols, algorithms, and concepts.
  3. **Completeness & Edge Cases [0–20]**: Coverage of operational edge cases, concurrency, and failure modes.
  4. **Structure & Communication [0–20]**: Application of STAR methodology, modular paragraphs, and trade-off analysis.
  5. **Use of Concrete Examples [0–20]**: Reference to production tools, specific databases, and quantitative metrics.
- **Defense Mechanism**: Pre-evaluation adversarial regex filter neutralizing prompt injections (`PROMPT_INJECTION_PATTERNS`).
- **License**: Academic / Educational Open Source (MIT)

## Intended Use
- **Primary Use Case**: Formative self-coaching for students preparing for campus technical placement interviews.
- **Input Modality**: Typed-first technical responses ($\ge 20$ characters).
- **Prohibited Modalities & Inferences**:
  - Voice recording, speech prosody, or vocal tone analysis.
  - Video facial recognition, emotion detection, or gaze tracking.
  - Inferring personality traits, honesty, truthfulness, or psychological state.

## Safety & Quality Assurance
- **Score Bounding**: Strict clamping $[0.0, 20.0]$ per dimension, $[0.0, 100.0]$ total score.
- **Evidence Verification**: Positive coaching highlights must be exact verbatim substrings extracted from the candidate's typed text.
- **Immutable Auditing**: All evaluations logged in `InterviewAudit` with provider metadata, prompt injection detection flag, and latency profiling.
- **Mandatory Statutory Disclaimer**:
  > *"CareerPilot AI mock interview scores evaluate written technical articulation and structured reasoning against standardized rubrics. They do not predict interview callbacks or hiring outcomes, nor guarantee placement. The platform does not analyze voice, video, or biometric indicators."*
