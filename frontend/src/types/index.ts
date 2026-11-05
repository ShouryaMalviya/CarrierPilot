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
  skill_id: number;
  canonical_name: string;
  category: string;
  confidence_score: number;
  evidence_snippet: string | null;
  is_user_confirmed: boolean;
}

export interface Resume {
  id: number;
  original_filename: string;
  file_size_bytes: number;
  mime_type: string;
  parse_status: string;
  created_at: string;
  skills: ResumeSkill[];
}

export interface Job {
  id: number;
  title: string;
  company: string | null;
  description: string;
  source_url: string | null;
  is_synthetic: boolean;
  is_active: boolean;
  required_skills: string[];
  preferred_skills: string[];
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
  difficulty: 'easy' | 'medium' | 'hard';
  question_text: string;
  options: QuestionOption[];
}

export interface AttemptFeedback {
  is_correct: boolean;
  score: number;
  answer_key: string;
  explanation: string;
}

export interface TopicMastery {
  topic: string;
  mastery_score: number;
  recent_attempts_count: number;
  accuracy_percentage: number;
  status_tier: 'mastered' | 'proficient' | 'developing' | 'needs_practice' | 'unattempted';
  reason_codes: string[];
}

export interface DashboardProgress {
  streak_days: number;
  longest_streak_days: number;
  total_attempts: number;
  correct_attempts: number;
  overall_accuracy_percentage: number;
  completed_sessions_count: number;
  active_sessions_count: number;
  readiness: {
    overall_readiness_score: number;
    profile_resume_score: number;
    practice_mastery_score: number;
    job_matching_score: number;
    mock_interview_score: number;
    readiness_level: 'beginner' | 'developing' | 'placement_ready';
    disclaimer: string;
  };
  topic_masteries: TopicMastery[];
  activity_timeline: Array<{
    date: string;
    attempt_count: number;
    correct_count: number;
    duration_seconds: number;
  }>;
  next_action: {
    action_type: string;
    title: string;
    description: string;
    target_topic: string | null;
    target_url: string | null;
  };
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
