# Model Card: Explainable Hybrid Job Matching Engine

## Model Details
- **Model Name**: CareerPilot Hybrid Job Ranker (v1.0.0)
- **Model Type**: Hybrid Information Retrieval Ranker combining Normalized Lexical Skill Overlap and Cosine Text Similarity.
- **Components**:
  - 50% Required Skill Coverage ($S_{\text{req}} = \frac{|K_{\text{cand}} \cap K_{\text{job,req}}|}{|K_{\text{job,req}}|}$)
  - 20% Preferred Skill Coverage ($S_{\text{pref}} = \frac{|K_{\text{cand}} \cap K_{\text{job,pref}}|}{|K_{\text{job,pref}}|}$)
  - 30% Similarity Score (TF-IDF Cosine Similarity or SentenceTransformer Semantic Embedding Cosine Similarity)
- **License**: Academic / Educational Open Source (MIT)

## Intended Use
- **Primary Use Case**: Guiding university students in identifying skill gaps and curriculum alignment relative to technical job descriptions.
- **Target Users**: Graduating engineering students, campus placement cells, and career counselors.
- **Out-of-Scope / Prohibited Uses**:
  - Automated candidate filtering or screening by hiring managers.
  - Making employment rejection or hiring decisions.
  - Claiming to predict real-world interview callbacks or hiring probabilities.

## Factors & Performance Metrics
- **Evaluated on Frozen Benchmark**: 5 fresh graduate profiles across 5 technology domains (Python Backend, Data Analyst, Frontend, DevOps, ML Engineer).
- **Mean Reciprocal Rank (MRR)**: **1.0000**
- **Mean Recall@3**: **1.0000**
- **Mean nDCG@3**: **0.9966**
- **Mean Precision@1**: **1.0000**

## Ethical Considerations & Limitations
- **Text Alignment Only**: Scores reflect textual alignment between the uploaded resume document and the job description. High scores do not certify real-world software engineering competence.
- **Synonym Normalization**: Relies on a canonical taxonomy dictionary (`app/services/skill_taxonomy.py`) with user confirmation controls to mitigate vocabulary divergence.
- **Mandatory Disclaimer**: Every API response delivers the statutory educational disclaimer:
  > *"Match scores reflect automated text overlap and skill taxonomy alignment for self-assessment. They do not predict interview invitations or hiring outcomes, nor guarantee placement."*

