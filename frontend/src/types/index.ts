/**
 * Core TypeScript definitions matching backend API v1 schemas.
 */

export interface User {
  id: number;
  email: string;
  is_active: boolean;
  is_verified: boolean;
  created_at: string;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  user: User;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
}

export interface Profile {
  id: number;
  user_id: number;
  target_role: string;
  preferred_language: string;
  consent_analytics: boolean;
  created_at: string;
  updated_at: string;
}

export interface ProfileUpdate {
  target_role?: string;
  preferred_language?: string;
  consent_analytics?: boolean;
}

export interface OnboardingDisclosure {
  purpose: string;
  disclaimers: string[];
  data_retention_policy: string;
  camera_or_mic_required: boolean;
  supported_roles: string[];
}

export interface ResumeSkill {
  id: number;
  resume_id?: number;
  skill_id: number;
  canonical_name: string;
  category: string;
  confidence_score: number;
  evidence_snippet: string | null;
  is_user_confirmed: boolean;
  is_auto_extracted?: boolean;
  created_at?: string;
}

export interface Resume {
  id: number;
  user_id?: number;
  original_filename: string;
  file_size_bytes: number;
  mime_type: string;
  parse_status: 'pending' | 'success' | 'warning' | 'error' | string;
  parser_version?: string | null;
  parsed_content?: {
    char_count?: number;
    word_count?: number;
    line_count?: number;
    sections?: Record<string, string>;
    [key: string]: any;
  } | null;
  created_at: string;
  updated_at?: string;
  skills?: ResumeSkill[];
}

export interface ResumeSectionsResponse {
  resume_id: number;
  sections: Record<string, string>;
  skills: ResumeSkill[];
}

export interface ResumeListResponse {
  resumes: Resume[];
  total: number;
}

export interface JobSkillResponse {
  id: number;
  skill_id: number;
  canonical_name: string;
  category: string;
  is_required: boolean;
}

export interface Job {
  id: number;
  user_id?: number;
  title: string;
  company: string | null;
  description: string;
  source_url: string | null;
  is_synthetic: boolean;
  is_active: boolean;
  required_skills: string[];
  preferred_skills: string[];
  skills?: JobSkillResponse[];
  created_at?: string;
  updated_at?: string;
}

export interface JobListResponse {
  jobs: Job[];
  total: number;
}

export interface JobCreate {
  title: string;
  company?: string | null;
  description: string;
  source_url?: string | null;
  required_skills?: string[];
  preferred_skills?: string[];
}

export interface SkillGapBreakdown {
  matched_required: string[];
  missing_required: string[];
  matched_preferred: string[];
  missing_preferred: string[];
  additional_skills: string[];
}

export interface MatchedSkillEvidence {
  canonical_name: string;
  category: string;
  is_required: boolean;
  evidence_snippet: string | null;
  confidence_score?: number;
  is_user_confirmed?: boolean;
}

export interface LearningRecommendation {
  skill_name: string;
  category: string;
  priority: string;
  rationale: string;
  suggested_action: string;
}

export interface MatchScoreBreakdown {
  required_coverage: number;
  preferred_coverage: number;
  tfidf_similarity: number;
  semantic_similarity: number | null;
  overall_score: number;
  similarity_mode: string;
  is_fallback: boolean;
  fallback_reason: string | null;
  applied_weights?: Record<string, number>;
}

export interface LexicalMatchResponse {
  resume_id: number;
  job_id: number;
  job_title: string;
  company: string | null;
  scores: MatchScoreBreakdown;
  skill_gap: SkillGapBreakdown;
  evidence: MatchedSkillEvidence[];
  recommendations: LearningRecommendation[];
  explanation_summary: string;
  disclaimer: string;
}

export interface BatchMatchItem {
  job_id: number;
  job_title: string;
  company: string | null;
  is_synthetic: boolean;
  overall_score: number;
  required_coverage: number;
  preferred_coverage: number;
  tfidf_similarity: number;
  semantic_similarity: number | null;
  similarity_mode: string;
  is_fallback: boolean;
  missing_required_count: number;
  missing_required: string[];
}

export interface BatchMatchResponse {
  resume_id: number;
  total_jobs_evaluated: number;
  matches: BatchMatchItem[];
  disclaimer: string;
}

export interface SemanticStatusResponse {
  is_available: boolean;
  model_name: string;
  provider_type: string;
  fallback_mode: boolean;
  last_error: string | null;
}

export interface HybridMatchResult {
  job_id: number;
  job_title: string;
  company: string | null;
  hybrid_score: number;
  required_coverage: number;
  preferred_coverage: number;
  semantic_similarity: number;
  matched_required_skills: string[];
  missing_required_skills: string[];
  disclaimer: string;
}

export interface QuestionOption {
  key: string;
  text: string;
}

export interface PracticeQuestion {
  id: number;
  topic: string;
  difficulty: 'easy' | 'medium' | 'hard' | string;
  question_text: string;
  options: QuestionOption[];
}

export interface PracticeSession {
  id: string;
  user_id: number;
  topic: string;
  difficulty: string | null;
  status: 'in_progress' | 'completed' | 'abandoned';
  total_questions: number;
  current_index: number;
  current_question: PracticeQuestion | null;
  score: number | null;
  created_at: string;
  completed_at: string | null;
}

export interface PracticeTopicSummary {
  topic: string;
  total_questions: number;
  difficulty_counts: Record<string, number>;
}

export interface AttemptFeedback {
  attempt_id?: number;
  question_id: number;
  session_id?: string | null;
  user_answer: string;
  is_correct: boolean;
  score: number;
  correct_answer_key: string;
  explanation: string;
  duration_seconds?: number | null;
  created_at?: string;
}

export interface TopicMastery {
  topic: string;
  mastery_score: number;
  recent_attempts_count: number;
  accuracy_percentage: number;
  status_tier: 'mastered' | 'proficient' | 'developing' | 'needs_practice' | 'unattempted';
  reason_codes: string[];
}

export interface DailyActivity {
  date: string;
  attempt_count: number;
  correct_count: number;
  duration_seconds: number;
}

export interface NextRecommendedAction {
  action_type: 'upload_resume' | 'start_practice' | 'remediate_weak_topic' | 'advance_challenge' | 'mock_interview' | 'explore_jobs' | string;
  title: string;
  description: string;
  target_topic: string | null;
  target_url: string | null;
}

export interface ReadinessBreakdown {
  overall_readiness_score: number;
  profile_resume_score: number;
  practice_mastery_score: number;
  job_matching_score: number;
  mock_interview_score: number;
  readiness_level: 'beginner' | 'developing' | 'placement_ready' | 'interview_ready';
  disclaimer: string;
}

export interface DashboardProgress {
  user_id: number;
  target_role: string;
  streak_days: number;
  longest_streak_days: number;
  total_attempts: number;
  correct_attempts: number;
  overall_accuracy_percentage: number;
  total_practice_time_seconds: number;
  completed_sessions_count: number;
  active_sessions_count: number;
  readiness: ReadinessBreakdown;
  topic_masteries: TopicMastery[];
  activity_timeline: DailyActivity[];
  next_action: NextRecommendedAction;
  generated_at: string;
}

export interface CuratedInterviewQuestion {
  id: string;
  role: string;
  competency: string;
  question_text: string;
  guidelines: string[];
  key_concepts: string[];
}

export interface InterviewCatalogResponse {
  total: number;
  roles: string[];
  competencies: string[];
  questions: CuratedInterviewQuestion[];
}

export interface InterviewSessionListResponse {
  total: number;
  sessions: InterviewSession[];
}

export interface DimensionScore {
  dimension: string;
  label: string;
  score: number;
  max_score: number;
  feedback: string;
  positive_evidence: string[];
}

export interface RubricFeedback {
  rubric_version: string;
  total_score: number;
  dimension_scores: Record<string, DimensionScore>;
  key_concepts_covered: string[];
  key_concepts_missed: string[];
  positive_highlights: string[];
  actionable_improvements: string[];
  summary: string;
  disclaimer: string;
}

export interface InterviewSession {
  id: number;
  user_id: number;
  role: string;
  competency: string;
  question_text: string;
  status: 'in_progress' | 'submitted' | 'completed' | 'abandoned';
  user_response: string | null;
  total_score: number | null;
  feedback_json: RubricFeedback | null;
  model_provider: string;
  disclaimer: string;
  created_at: string;
  updated_at: string;
}
