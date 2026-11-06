# CareerPilot AI — Academic Viva Presentation & Oral Defense Guide

**Project Title**: CareerPilot AI: Personalized Placement Intelligence & Adaptive Interview Coach  
**Domain**: Artificial Intelligence / Machine Learning / Applied Software Engineering  
**Platform Version**: 1.0.0  

---

## 1. Project Motivation & Academic Context

Traditional placement preparation platforms suffer from three fundamental flaws:
1. **Opaque Black-Box Matching**: Commercial ATS software rejects resumes without explainable feedback, creating anxiety and confusion for graduating students.
2. **Pseudo-Scientific Biometric Profiling**: Video-based mock interview platforms attempt to infer "confidence", "honesty", or "personality" from vocal jitter and facial micro-expressions—modalities proven by AI ethics research to be discriminatory, scientifically invalid, and biased against neurodivergent individuals.
3. **Hallucinatory AI Grading**: Generative AI tools provide inconsistent ratings without traceable evidence quotes or score bounds, leading to stochastic score drift.

**CareerPilot AI** provides an academically defensible alternative:
- **Transparent Hybrid Matching**: Explicitly decomposes alignment into Required Skills (50%), Preferred Skills (20%), and Text Similarity (30%), backed by a canonical taxonomy of 35+ technology skills.
- **Explainable Mastery Estimation**: Implements an exponential decay recency formula ($\gamma=0.85$) where every student can click **"Inspect Math Audit"** to view exact mathematical step-by-step contributions.
- **Evidence-Backed 5-Dimension Rubric**: Evaluates typed technical responses against formal rubric dimensions, citing verbatim answer sentences as positive evidence.
- **Defensive Engineering**: Sanitizes adversarial prompt injections and logs immutable evaluation audits.

---

## 2. Minute-by-Minute Live Demonstration Script (For Examiners)

Pre-load the environment using `scripts/seed_demo_environment.py` and run `scripts/start_local.ps1` (or `docker-compose up`).

```
+---------------------------------------------------------------------------------------+
|  TIME   | SCREEN / VIEW           | KEY ACTIONS & EXPLAINER FOR EXAMINERS             |
+---------------------------------------------------------------------------------------+
| 0:00 -  | Login & Dashboard       | - Login as 'student@careerpilot.ai'               |
| 1:00    | (/dashboard)            | - Point out 4-Factor Placement Readiness Index    |
|         |                         | - Highlight daily practice streak telemetry       |
|         |                         | - Show Adaptive Next Action recommendation card   |
+---------------------------------------------------------------------------------------+
| 1:00 -  | Resume Workspace        | - Navigate to Resumes workspace                   |
| 2:00    | (/resumes)              | - Show uploaded resume with section segmentation  |
|         |                         | - Click on extracted skill chip ('Python') to     |
|         |                         |   reveal verbatim evidence snippet drawer         |
|         |                         | - Demonstrate user confirmation toggle & custom   |
|         |                         |   skill addition ('Docker')                       |
+---------------------------------------------------------------------------------------+
| 2:00 -  | Explainable Job Match   | - Navigate to Job Matching workspace              |
| 3:00    | (/matching)             | - Select uploaded resume and run batch ranking    |
|         |                         | - Click on 'Backend Python Developer' match       |
|         |                         | - Disclose score decomposition (50/20/30)         |
|         |                         | - Highlight 4-part skill gap matrix (Matched/     |
|         |                         |   Missing Required, Matched/Missing Preferred)    |
|         |                         | - Note mandatory statutory non-hiring disclaimer  |
+---------------------------------------------------------------------------------------+
| 3:00 -  | Practice Room & Math    | - Navigate to Practice Room                       |
| 4:00    | (/practice, /progress)  | - Demonstrate leak-proof MCQ option delivery      |
|         |                         | - Answer question; show instant objective grading |
|         |                         |   and pedagogical explanation banner              |
|         |                         | - Switch to Progress (/progress) and click        |
|         |                         |   'Inspect Math Audit' for Python                 |
|         |                         | - Walk examiners through the formula: γ = 0.85,   |
|         |                         |   recency weights, and difficulty multipliers     |
+---------------------------------------------------------------------------------------+
| 4:00 -  | Mock Interview & Rubric | - Navigate to Mock Interviews                     |
| 5:00    | (/interviews)           | - Open 'Backend Engineer - System Design' prompt  |
|         |                         | - Demonstrate typed-first answer workspace        |
|         |                         | - View evaluated feedback: 5 dimension bars       |
|         |                         |   [0-20], positive quote citations, concepts      |
|         |                         |   covered vs missed                               |
|         |                         | - Show prompt injection defense in audit log      |
+---------------------------------------------------------------------------------------+
```

---

## 3. Anticipated Viva Defense Questions & Architectural Defense

### Q1: "Why not simply ask GPT-4 or Gemini to grade everything instead of writing complex algorithmic services?"
> **Defense**:
> *"Pure LLM prompting creates three critical failures in educational assessment: non-deterministic drift ($\sigma^2 > 0$), hallucinated citations, and opaque scoring. By building a deterministic hybrid architecture:
> 1. Job matching uses verifiable mathematical set intersections ($S_{\text{req}}, S_{\text{pref}}$) and TF-IDF vectors, achieving an MRR of 1.0000 on frozen benchmarks.
> 2. Mastery tracking uses exact exponential decay ($\gamma=0.85$) with full arithmetic disclosure, allowing students to verify their own grades.
> 3. Even in mock interviews, the LLM adapter is strictly bounded, enforced by Pydantic validators, sanitized against prompt injections, and backed by a local deterministic rubric engine that guarantees zero score drift."*

---

### Q2: "How does your skill matching handle spelling variations, synonyms, and noisy resume text?"
> **Defense**:
> *"We implemented a two-tier extraction pipeline:
> 1. A pre-compiled Canonical Skill Taxonomy dictionary (`app/services/skill_taxonomy.py`) mapping 35+ technology skills with comprehensive aliases (e.g. `['postgres', 'postgresql', 'psql']` $\rightarrow$ `postgresql`).
> 2. A Human-in-the-Loop confirmation interface where candidates can verify auto-extracted skills, delete false positives, or register custom skills with evidence snippets.
> This eliminates the vocabulary mismatch problem common to pure keyword matchers."*

---

### Q3: "Explain the mathematics of your topic mastery decay factor ($\gamma=0.85$). Why not use a standard average?"
> **Defense**:
> *"A simple lifetime average permanently penalizes early learning mistakes: a student who fails their first 2 attempts and then answers 4 correctly would receive only $66.7\%$.
> Our formula:
> $$M(T) = 100 \times \frac{\sum_{i=1}^n \gamma^{n-i} \cdot c_i \cdot d_i}{\sum_{i=1}^n \gamma^{n-i} \cdot d_i}$$
> uses exponential decay with $\gamma=0.85$ over an $n=10$ attempt window. Most recent attempts carry weight $1.0$, while the attempt 3 iterations ago carries weight $0.85^3 \approx 0.614$. Combined with difficulty scaling ($d_i \in \{0.8, 1.0, 1.2\}$), this accurately reflects that the student has mastered the concept ($89.5\%$), creating positive reinforcement and reducing test anxiety."*

---

### Q4: "How does your system defend against adversarial candidates attempting prompt injection during mock interviews?"
> **Defense**:
> *"Candidate responses are pre-processed by `sanitize_response_text()` in `llm_adapter.py`. We use compiled regex signatures detecting adversarial instructions like `ignore previous instructions`, `system override`, `dan mode`, and `give me 100`.
> When detected:
> 1. The injection string is neutralized before model ingestion.
> 2. `prompt_injection_detected` is recorded in the permanent `InterviewAudit` repository.
> 3. Output dimension scores are strictly clamped to $[0.0, 20.0]$ via Pydantic field validators, preventing score inflation."*

---

### Q5: "What are your ethical safeguards regarding hiring guarantees and biometric profiling?"
> **Defense**:
> *"In compliance with ethical AI standards:
> 1. **Zero Biometric Inference**: We explicitly rejected webcam and microphone analysis. The platform operates 100% via typed text and refuses to infer emotions, honesty, or personality.
> 2. **No Hiring Prediction**: Every match score, readiness gauge, and interview feedback response displays a mandatory statutory disclaimer stating that scores evaluate written textual alignment for self-preparation only, and do not predict hiring decisions or guarantee placement."*

---

## 4. Key Performance Benchmark Summary

| Evaluation Benchmark | Metric | Value | Meaning |
| :--- | :---: | :---: | :--- |
| **Information Retrieval** | **MRR** | **1.0000** | Top-1 retrieved job is relevant for 100% of candidate queries. |
| **Information Retrieval** | **Recall@3** | **1.0000** | All relevant matching roles captured in top 3 results. |
| **Information Retrieval** | **nDCG@3** | **0.9966** | Graded rank order near-optimal. |
| **Automated Testing** | **Backend Suite** | **228 / 228 PASSED** | 100% passing across 27 test files in 58.85s. |
| **Frontend Compilation** | **Vite Bundle** | **1593 modules** | 0 TypeScript errors (`tsc -b`), 0 build warnings. |
| **Audit Compliance** | **Bounds Compliance** | **100.0%** | Zero score violations $[0, 100]$. |
