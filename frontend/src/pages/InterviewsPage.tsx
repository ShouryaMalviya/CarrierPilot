import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  MessageSquare,
  Clock,
  ArrowRight,
  AlertCircle,
  Check,
  Play,
  RotateCcw,
  Lightbulb,
} from 'lucide-react';
import { useAlert } from '../context/AlertContext';
import { useAuth } from '../context/AuthContext';
import { api } from '../services/api';
import {
  CuratedInterviewQuestion,
  InterviewCatalogResponse,
  InterviewSession,
  InterviewSessionListResponse,
  RubricFeedback,
} from '../types';
import { Card } from '../components/common/Card';
import { Button } from '../components/common/Button';
import { Badge } from '../components/common/Badge';
import { EthicalDisclaimerBanner } from '../components/common/EthicalDisclaimerBanner';

type ViewMode = 'catalog' | 'studio' | 'feedback';

const MIN_RESPONSE_LENGTH = 20;

export const InterviewsPage: React.FC = () => {
  const { profile } = useAuth();
  const { showAlert } = useAlert();
  const navigate = useNavigate();

  // Mode state
  const [viewMode, setViewMode] = useState<ViewMode>('catalog');

  // Catalog & History state
  const [catalogQuestions, setCatalogQuestions] = useState<CuratedInterviewQuestion[]>([]);
  const [roles, setRoles] = useState<string[]>([]);
  const [competencies, setCompetencies] = useState<string[]>([]);
  const [selectedRoleFilter, setSelectedRoleFilter] = useState<string>('all');
  const [selectedCompFilter, setSelectedCompFilter] = useState<string>('all');
  const [isLoadingCatalog, setIsLoadingCatalog] = useState<boolean>(true);
  const [pastSessions, setPastSessions] = useState<InterviewSession[]>([]);

  // Studio / Active Session state
  const [activeSession, setActiveSession] = useState<InterviewSession | null>(null);
  const [typedResponse, setTypedResponse] = useState<string>('');
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const [sessionStartTime, setSessionStartTime] = useState<number>(Date.now());
  const [elapsedSeconds, setElapsedSeconds] = useState<number>(0);

  // Feedback state
  const [feedbackData, setFeedbackData] = useState<RubricFeedback | null>(null);
  const [isLoadingFeedback, setIsLoadingFeedback] = useState<boolean>(false);
  const [showAnswerReview, setShowAnswerReview] = useState<boolean>(false);

  // Load catalog and past sessions on mount
  const fetchCatalogAndHistory = async () => {
    setIsLoadingCatalog(true);
    try {
      const [catalogRes, sessionsRes] = await Promise.all([
        api.get<InterviewCatalogResponse>('/interviews/catalog'),
        api.get<InterviewSessionListResponse>('/interviews/sessions?limit=20'),
      ]);

      setCatalogQuestions(catalogRes.questions || []);
      setRoles(catalogRes.roles || []);
      setCompetencies(catalogRes.competencies || []);
      setPastSessions(sessionsRes.sessions || []);
    } catch (err: any) {
      showAlert(err?.message || 'Failed to load interview catalog.', 'danger');
    } finally {
      setIsLoadingCatalog(false);
    }
  };

  useEffect(() => {
    fetchCatalogAndHistory();
  }, []);

  // Studio timer effect
  useEffect(() => {
    let timer: any = null;
    if (viewMode === 'studio') {
      timer = setInterval(() => {
        setElapsedSeconds(Math.floor((Date.now() - sessionStartTime) / 1000));
      }, 1000);
    }
    return () => clearInterval(timer);
  }, [viewMode, sessionStartTime]);

  // Start new interview session
  const handleStartSession = async (question: CuratedInterviewQuestion) => {
    try {
      const session = await api.post<InterviewSession>('/interviews/sessions', {
        role: question.role,
        competency: question.competency,
        curated_question_id: question.id,
      });

      setActiveSession(session);
      setTypedResponse('');
      setFeedbackData(null);
      setSessionStartTime(Date.now());
      setElapsedSeconds(0);
      setViewMode('studio');
      showAlert(`Interview session started: ${question.competency} prompt.`, 'success');
    } catch (err: any) {
      showAlert(err?.data?.error?.message || err?.message || 'Failed to start interview session.', 'danger');
    }
  };

  // Submit response for rubric evaluation
  const handleSubmitResponse = async () => {
    if (!activeSession) return;
    if (typedResponse.trim().length < MIN_RESPONSE_LENGTH) {
      showAlert(`Response must be at least ${MIN_RESPONSE_LENGTH} characters long.`, 'warning');
      return;
    }

    setIsSubmitting(true);
    try {
      const updated = await api.post<InterviewSession>(
        `/interviews/sessions/${activeSession.id}/submit`,
        { user_response: typedResponse.trim() }
      );

      setActiveSession(updated);

      // Fetch evaluated rubric feedback
      const feedback = await api.get<RubricFeedback>(
        `/interviews/sessions/${activeSession.id}/feedback`
      );
      setFeedbackData(feedback);
      setViewMode('feedback');
      showAlert('Response evaluated against 5-dimension coaching rubric!', 'success');
      fetchCatalogAndHistory(); // refresh past history in background
    } catch (err: any) {
      showAlert(err?.data?.error?.message || err?.message || 'Failed to evaluate interview response.', 'danger');
    } finally {
      setIsSubmitting(false);
    }
  };

  // Inspect past session feedback
  const handleInspectFeedback = async (session: InterviewSession) => {
    setActiveSession(session);
    setTypedResponse(session.user_response || '');
    setIsLoadingFeedback(true);
    setViewMode('feedback');

    try {
      const feedback = await api.get<RubricFeedback>(`/interviews/sessions/${session.id}/feedback`);
      setFeedbackData(feedback);
    } catch (err: any) {
      showAlert(err?.message || 'Failed to load session rubric feedback.', 'danger');
    } finally {
      setIsLoadingFeedback(false);
    }
  };

  // Abandon active session
  const handleAbandonSession = async () => {
    if (!activeSession) return;
    if (!window.confirm('Are you sure you want to abandon this interview session?')) return;

    try {
      await api.post(`/interviews/sessions/${activeSession.id}/abandon`);
      showAlert('Session abandoned.', 'info');
      setViewMode('catalog');
      setActiveSession(null);
      fetchCatalogAndHistory();
    } catch (err: any) {
      showAlert(err?.message || 'Failed to abandon session.', 'danger');
    }
  };

  const formatTimer = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs < 10 ? '0' : ''}${secs}`;
  };

  const getScoreColor = (score: number) => {
    if (score >= 80) return 'var(--success-600)';
    if (score >= 60) return 'var(--primary-600)';
    if (score >= 40) return 'var(--warning-600)';
    return 'var(--danger-600)';
  };

  // Filter curated questions
  const filteredQuestions = catalogQuestions.filter((q) => {
    const roleMatch = selectedRoleFilter === 'all' || q.role.toLowerCase() === selectedRoleFilter.toLowerCase();
    const compMatch = selectedCompFilter === 'all' || q.competency.toLowerCase() === selectedCompFilter.toLowerCase();
    return roleMatch && compMatch;
  });

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
      <EthicalDisclaimerBanner />

      {/* Header */}
      <div style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', justifyContent: 'space-between', gap: '16px' }}>
        <div>
          <h2 style={{ fontSize: '1.625rem', fontWeight: 800, color: 'var(--slate-900)', margin: 0 }}>
            Mock Interview Coaching Studio
          </h2>
          <p style={{ color: 'var(--slate-500)', fontSize: '0.875rem', marginTop: '4px', margin: 0 }}>
            Typed-first technical & behavioral interview prompts evaluated objectively with quote evidence citations.
          </p>
        </div>

        {viewMode !== 'catalog' && (
          <Button variant="outline" size="sm" onClick={() => setViewMode('catalog')} icon={<RotateCcw size={14} />}>
            Back to Interview Catalog
          </Button>
        )}
      </div>

      {/* ========================================================================= */}
      {/* 1. CATALOG & HISTORY VIEW                                                 */}
      {/* ========================================================================= */}
      {viewMode === 'catalog' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
          {/* Filter Bar */}
          <div
            style={{
              padding: '16px 20px',
              backgroundColor: '#ffffff',
              borderRadius: 'var(--radius-lg)',
              border: '1px solid var(--slate-200)',
              display: 'flex',
              flexWrap: 'wrap',
              alignItems: 'center',
              justifyContent: 'space-between',
              gap: '16px',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px', flexWrap: 'wrap' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <span style={{ fontSize: '0.8125rem', fontWeight: 600, color: 'var(--slate-700)' }}>
                  Filter by Role:
                </span>
                <select
                  className="input"
                  style={{ width: 'auto' }}
                  value={selectedRoleFilter}
                  onChange={(e) => setSelectedRoleFilter(e.target.value)}
                >
                  <option value="all">All Roles ({catalogQuestions.length})</option>
                  {roles.map((r) => (
                    <option key={r} value={r}>
                      {r}
                    </option>
                  ))}
                </select>
              </div>

              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <span style={{ fontSize: '0.8125rem', fontWeight: 600, color: 'var(--slate-700)' }}>
                  Competency:
                </span>
                <select
                  className="input"
                  style={{ width: 'auto' }}
                  value={selectedCompFilter}
                  onChange={(e) => setSelectedCompFilter(e.target.value)}
                >
                  <option value="all">All Competencies ({competencies.length})</option>
                  {competencies.map((c) => (
                    <option key={c} value={c}>
                      {c}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            <Badge variant="primary">
              Target Profile: {profile?.target_role || 'Junior Python Developer'}
            </Badge>
          </div>

          {/* Curated Question Cards Grid */}
          <div>
            <h3 style={{ fontSize: '1.125rem', fontWeight: 700, color: 'var(--slate-900)', marginBottom: '14px' }}>
              Curated Interview Prompts ({filteredQuestions.length})
            </h3>

            {isLoadingCatalog ? (
              <div style={{ padding: '40px', textAlign: 'center', color: 'var(--slate-500)' }}>
                Loading interview question catalog...
              </div>
            ) : filteredQuestions.length === 0 ? (
              <Card>
                <div style={{ padding: '32px', textAlign: 'center', color: 'var(--slate-500)' }}>
                  No curated questions match your role and competency filters.
                </div>
              </Card>
            ) : (
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(340px, 1fr))', gap: '16px' }}>
                {filteredQuestions.map((q) => (
                  <div
                    key={q.id}
                    style={{
                      padding: '20px',
                      borderRadius: 'var(--radius-lg)',
                      backgroundColor: '#ffffff',
                      border: '1px solid var(--slate-200)',
                      boxShadow: 'var(--shadow-sm)',
                      display: 'flex',
                      flexDirection: 'column',
                      justifyContent: 'space-between',
                      gap: '16px',
                    }}
                  >
                    <div>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '10px' }}>
                        <Badge variant="primary">{q.competency}</Badge>
                        <Badge variant="neutral">{q.role}</Badge>
                      </div>

                      <h4 style={{ fontSize: '0.9375rem', fontWeight: 700, color: 'var(--slate-900)', lineHeight: 1.5, margin: '0 0 10px' }}>
                        {q.question_text}
                      </h4>

                      {/* Key Concepts Preview */}
                      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '4px' }}>
                        {q.key_concepts.slice(0, 3).map((concept, idx) => (
                          <span
                            key={idx}
                            style={{
                              fontSize: '0.6875rem',
                              padding: '2px 6px',
                              backgroundColor: 'var(--slate-100)',
                              borderRadius: 'var(--radius-sm)',
                              color: 'var(--slate-600)',
                            }}
                          >
                            {concept}
                          </span>
                        ))}
                        {q.key_concepts.length > 3 && (
                          <span style={{ fontSize: '0.6875rem', color: 'var(--slate-400)', alignSelf: 'center' }}>
                            +{q.key_concepts.length - 3} more
                          </span>
                        )}
                      </div>
                    </div>

                    <Button
                      size="sm"
                      variant="primary"
                      onClick={() => handleStartSession(q)}
                      style={{ width: '100%', justifyContent: 'center' }}
                      icon={<Play size={14} />}
                    >
                      Start Mock Interview
                    </Button>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Past Mock Interview Sessions History */}
          {pastSessions.length > 0 && (
            <div>
              <h3 style={{ fontSize: '1.125rem', fontWeight: 700, color: 'var(--slate-900)', marginBottom: '14px' }}>
                Past Mock Interview Sessions ({pastSessions.length})
              </h3>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                {pastSessions.map((s) => (
                  <div
                    key={s.id}
                    style={{
                      padding: '14px 18px',
                      borderRadius: 'var(--radius-md)',
                      backgroundColor: '#ffffff',
                      border: '1px solid var(--slate-200)',
                      display: 'flex',
                      flexWrap: 'wrap',
                      alignItems: 'center',
                      justifyContent: 'space-between',
                      gap: '12px',
                    }}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                      <div
                        style={{
                          width: '36px',
                          height: '36px',
                          borderRadius: '8px',
                          backgroundColor: s.status === 'completed' ? 'var(--success-bg)' : 'var(--slate-100)',
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'center',
                          color: s.status === 'completed' ? 'var(--success-icon)' : 'var(--slate-500)',
                          flexShrink: 0,
                        }}
                      >
                        <MessageSquare size={18} />
                      </div>
                      <div>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                          <span style={{ fontWeight: 700, fontSize: '0.875rem', color: 'var(--slate-800)' }}>
                            {s.competency} ({s.role})
                          </span>
                          <Badge variant={s.status === 'completed' ? 'success' : 'neutral'}>
                            {s.status.toUpperCase()}
                          </Badge>
                        </div>
                        <span style={{ fontSize: '0.75rem', color: 'var(--slate-500)', display: 'block', marginTop: '2px' }}>
                          {new Date(s.created_at).toLocaleDateString()} • {s.question_text.slice(0, 60)}...
                        </span>
                      </div>
                    </div>

                    <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
                      {s.total_score !== null && (
                        <div style={{ textAlign: 'right' }}>
                          <span style={{ fontSize: '1.25rem', fontWeight: 800, color: getScoreColor(s.total_score) }}>
                            {s.total_score.toFixed(0)}/100
                          </span>
                          <span style={{ display: 'block', fontSize: '0.6875rem', color: 'var(--slate-400)' }}>
                            Rubric Score
                          </span>
                        </div>
                      )}

                      {s.status === 'completed' ? (
                        <Button size="sm" variant="outline" onClick={() => handleInspectFeedback(s)}>
                          View Rubric Feedback
                        </Button>
                      ) : (
                        <Button size="sm" variant="primary" onClick={() => { setActiveSession(s); setTypedResponse(s.user_response || ''); setViewMode('studio'); }}>
                          Resume Response
                        </Button>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* ========================================================================= */}
      {/* 2. TYPED RESPONSE STUDIO VIEW                                             */}
      {/* ========================================================================= */}
      {viewMode === 'studio' && activeSession && (
        <div style={{ maxWidth: '860px', margin: '0 auto', width: '100%', display: 'flex', flexDirection: 'column', gap: '20px' }}>
          {/* Top Session Status Bar */}
          <div
            style={{
              padding: '14px 20px',
              backgroundColor: '#ffffff',
              borderRadius: 'var(--radius-lg)',
              border: '1px solid var(--slate-200)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              gap: '12px',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Badge variant="primary">{activeSession.competency}</Badge>
              <Badge variant="neutral">{activeSession.role}</Badge>
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.8125rem', color: 'var(--slate-600)', fontWeight: 600 }}>
                <Clock size={16} color="var(--primary-600)" />
                <span>Elapsed: {formatTimer(elapsedSeconds)}</span>
              </div>
              <Button size="sm" variant="outline" onClick={handleAbandonSession}>
                Exit Session
              </Button>
            </div>
          </div>

          {/* Prompt Card */}
          <div
            style={{
              padding: '28px',
              backgroundColor: '#ffffff',
              borderRadius: 'var(--radius-xl)',
              boxShadow: 'var(--shadow-sm)',
              border: '1px solid var(--slate-200)',
            }}
          >
            <span style={{ fontSize: '0.75rem', textTransform: 'uppercase', letterSpacing: '0.06em', color: 'var(--primary-600)', fontWeight: 700 }}>
              Interview Question Prompt
            </span>
            <h3 style={{ fontSize: '1.25rem', fontWeight: 800, color: 'var(--slate-900)', lineHeight: 1.5, margin: '8px 0 16px' }}>
              {activeSession.question_text}
            </h3>

            {/* STAR Coaching Guidelines Helper */}
            <div
              style={{
                padding: '14px 16px',
                backgroundColor: 'var(--primary-50)',
                border: '1px solid var(--primary-200)',
                borderRadius: 'var(--radius-md)',
                display: 'flex',
                alignItems: 'flex-start',
                gap: '12px',
              }}
            >
              <Lightbulb size={18} color="var(--primary-700)" style={{ flexShrink: 0, marginTop: '2px' }} />
              <div style={{ fontSize: '0.8125rem', color: 'var(--primary-900)', lineHeight: 1.5 }}>
                <strong>STAR Response Technique:</strong> Frame your answer around{' '}
                <strong>Situation</strong> (context), <strong>Task</strong> (objective),{' '}
                <strong>Action</strong> (concrete tools, code, metrics), and <strong>Result</strong> (measurable outcome).
              </div>
            </div>
          </div>

          {/* Candidate Response Workspace */}
          <div
            style={{
              padding: '24px',
              backgroundColor: '#ffffff',
              borderRadius: 'var(--radius-xl)',
              boxShadow: 'var(--shadow-sm)',
              border: '1px solid var(--slate-200)',
              display: 'flex',
              flexDirection: 'column',
              gap: '14px',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <label style={{ fontSize: '0.875rem', fontWeight: 700, color: 'var(--slate-800)' }}>
                Your Written Response:
              </label>
              <span
                style={{
                  fontSize: '0.75rem',
                  fontWeight: 600,
                  color: typedResponse.trim().length >= MIN_RESPONSE_LENGTH ? 'var(--success-600)' : 'var(--slate-400)',
                }}
              >
                {typedResponse.trim().length} characters{' '}
                {typedResponse.trim().length < MIN_RESPONSE_LENGTH && `(min ${MIN_RESPONSE_LENGTH})`}
              </span>
            </div>

            <textarea
              className="textarea"
              rows={12}
              style={{
                fontFamily: 'var(--font-sans)',
                fontSize: '0.875rem',
                lineHeight: 1.6,
                padding: '14px',
              }}
              placeholder="Type your structured answer here. Be specific about technologies, trade-offs, metrics, and outcomes..."
              value={typedResponse}
              onChange={(e) => setTypedResponse(e.target.value)}
            />

            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', paddingTop: '8px' }}>
              <span style={{ fontSize: '0.75rem', color: 'var(--slate-400)' }}>
                Camera & audio are never required. Responses are evaluated deterministically against rubric criteria.
              </span>

              <Button
                variant="primary"
                disabled={typedResponse.trim().length < MIN_RESPONSE_LENGTH || isSubmitting}
                isLoading={isSubmitting}
                onClick={handleSubmitResponse}
                icon={<ArrowRight size={16} />}
              >
                Submit Response for Rubric Evaluation
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* ========================================================================= */}
      {/* 3. 5-DIMENSION RUBRIC FEEDBACK VIEW                                       */}
      {/* ========================================================================= */}
      {viewMode === 'feedback' && activeSession && (
        <div style={{ maxWidth: '880px', margin: '0 auto', width: '100%', display: 'flex', flexDirection: 'column', gap: '24px' }}>
          {isLoadingFeedback && !feedbackData ? (
            <div style={{ padding: '60px', textAlign: 'center', color: 'var(--slate-500)', backgroundColor: '#ffffff', borderRadius: 'var(--radius-xl)' }}>
              <div
                style={{
                  width: '36px',
                  height: '36px',
                  border: '3px solid var(--slate-200)',
                  borderTopColor: 'var(--primary-600)',
                  borderRadius: '50%',
                  margin: '0 auto 12px',
                  animation: 'spin 0.8s linear infinite',
                }}
              />
              <p style={{ margin: 0, fontWeight: 600 }}>Analyzing candidate response across 5 rubric dimensions...</p>
            </div>
          ) : feedbackData ? (
            <>
              {/* Score Hero Banner */}
              <div
                style={{
                  background: 'linear-gradient(135deg, var(--primary-800), var(--primary-900))',
                  borderRadius: 'var(--radius-xl)',
                  padding: '32px',
                  color: '#ffffff',
                  boxShadow: 'var(--shadow-md)',
                  display: 'flex',
                  flexWrap: 'wrap',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  gap: '24px',
                }}
              >
                <div style={{ maxWidth: '540px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px' }}>
                    <Badge variant="primary" style={{ backgroundColor: 'rgba(255, 255, 255, 0.2)', color: '#ffffff' }}>
                      {activeSession.competency}
                    </Badge>
                    <Badge variant="neutral" style={{ backgroundColor: 'rgba(255, 255, 255, 0.1)', color: '#ffffff' }}>
                      Engine: {activeSession.model_provider || 'Deterministic Rubric'}
                    </Badge>
                  </div>
                  <h3 style={{ fontSize: '1.375rem', fontWeight: 800, margin: '0 0 8px', color: '#ffffff' }}>
                    Rubric Coaching Evaluation
                  </h3>
                  <p style={{ margin: 0, fontSize: '0.875rem', opacity: 0.9, lineHeight: 1.5 }}>
                    {feedbackData.summary}
                  </p>
                </div>

                {/* Big Score Gauge */}
                <div style={{ textAlign: 'center', backgroundColor: 'rgba(255, 255, 255, 0.1)', padding: '20px 28px', borderRadius: 'var(--radius-lg)' }}>
                  <div style={{ fontSize: '2.75rem', fontWeight: 900, color: '#ffffff', lineHeight: 1 }}>
                    {feedbackData.total_score.toFixed(0)}
                  </div>
                  <span style={{ fontSize: '0.75rem', textTransform: 'uppercase', letterSpacing: '0.08em', opacity: 0.85, fontWeight: 700 }}>
                    out of 100
                  </span>
                </div>
              </div>

              {/* 5-Dimension Sub-Scores */}
              <div>
                <h4 style={{ fontSize: '1.125rem', fontWeight: 800, color: 'var(--slate-900)', marginBottom: '14px' }}>
                  5-Dimension Performance Breakdown
                </h4>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
                  {Object.entries(feedbackData.dimension_scores).map(([key, dim]) => (
                    <div
                      key={key}
                      style={{
                        padding: '18px 20px',
                        borderRadius: 'var(--radius-lg)',
                        backgroundColor: '#ffffff',
                        border: '1px solid var(--slate-200)',
                        boxShadow: 'var(--shadow-sm)',
                        display: 'flex',
                        flexDirection: 'column',
                        gap: '10px',
                      }}
                    >
                      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                        <span style={{ fontWeight: 700, fontSize: '0.9375rem', color: 'var(--slate-800)' }}>
                          {dim.label}
                        </span>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                          <span style={{ fontSize: '1.125rem', fontWeight: 800, color: getScoreColor((dim.score / dim.max_score) * 100) }}>
                            {dim.score.toFixed(0)}/{dim.max_score}
                          </span>
                        </div>
                      </div>

                      {/* Dimension Progress Bar */}
                      <div style={{ height: '6px', backgroundColor: 'var(--slate-100)', borderRadius: '3px', overflow: 'hidden' }}>
                        <div
                          style={{
                            height: '100%',
                            width: `${(dim.score / dim.max_score) * 100}%`,
                            backgroundColor: getScoreColor((dim.score / dim.max_score) * 100),
                            borderRadius: '3px',
                          }}
                        />
                      </div>

                      <p style={{ margin: 0, fontSize: '0.8125rem', color: 'var(--slate-600)', lineHeight: 1.5 }}>
                        {dim.feedback}
                      </p>

                      {/* Verbatim Evidence Quotes */}
                      {dim.positive_evidence && dim.positive_evidence.length > 0 && (
                        <div
                          style={{
                            padding: '8px 12px',
                            backgroundColor: 'var(--slate-50)',
                            borderRadius: 'var(--radius-sm)',
                            border: '1px solid var(--slate-200)',
                            fontSize: '0.75rem',
                            color: 'var(--slate-600)',
                            fontStyle: 'italic',
                          }}
                        >
                          <strong>Verbatim Quote Evidence:</strong> "{dim.positive_evidence[0]}"
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>

              {/* Concepts Covered vs Missed */}
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
                <Card title="Concepts Covered" subtitle="Identified in your response">
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px', marginTop: '6px' }}>
                    {feedbackData.key_concepts_covered.length === 0 ? (
                      <span style={{ fontSize: '0.75rem', color: 'var(--slate-400)' }}>No target concepts detected.</span>
                    ) : (
                      feedbackData.key_concepts_covered.map((concept, idx) => (
                        <Badge key={idx} variant="success">
                          <Check size={12} /> {concept}
                        </Badge>
                      ))
                    )}
                  </div>
                </Card>

                <Card title="Concepts Missed" subtitle="Consider incorporating into future answers">
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px', marginTop: '6px' }}>
                    {feedbackData.key_concepts_missed.length === 0 ? (
                      <span style={{ fontSize: '0.75rem', color: 'var(--success-600)' }}>All key concepts addressed!</span>
                    ) : (
                      feedbackData.key_concepts_missed.map((concept, idx) => (
                        <Badge key={idx} variant="warning">
                          <AlertCircle size={12} /> {concept}
                        </Badge>
                      ))
                    )}
                  </div>
                </Card>
              </div>

              {/* Actionable Recommendations */}
              {feedbackData.actionable_improvements && feedbackData.actionable_improvements.length > 0 && (
                <Card title="Actionable Coaching Recommendations" subtitle="High-impact tips to elevate your score">
                  <ul style={{ margin: 0, paddingLeft: '20px', fontSize: '0.8125rem', color: 'var(--slate-700)', lineHeight: 1.6 }}>
                    {feedbackData.actionable_improvements.map((tip, idx) => (
                      <li key={idx} style={{ marginBottom: '6px' }}>
                        {tip}
                      </li>
                    ))}
                  </ul>
                </Card>
              )}

              {/* Toggle Candidate Answer Review */}
              <div style={{ padding: '16px 20px', backgroundColor: '#ffffff', borderRadius: 'var(--radius-lg)', border: '1px solid var(--slate-200)' }}>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                  <span style={{ fontWeight: 600, fontSize: '0.875rem', color: 'var(--slate-800)' }}>
                    Review Submitted Written Response
                  </span>
                  <Button size="sm" variant="outline" onClick={() => setShowAnswerReview(!showAnswerReview)}>
                    {showAnswerReview ? 'Hide Response' : 'Show Response'}
                  </Button>
                </div>

                {showAnswerReview && (
                  <div
                    style={{
                      marginTop: '12px',
                      padding: '12px 14px',
                      backgroundColor: 'var(--slate-50)',
                      borderRadius: 'var(--radius-md)',
                      fontSize: '0.8125rem',
                      color: 'var(--slate-800)',
                      whiteSpace: 'pre-wrap',
                      lineHeight: 1.6,
                      maxHeight: '260px',
                      overflowY: 'auto',
                    }}
                  >
                    {activeSession.user_response}
                  </div>
                )}
              </div>

              {/* Footnote & Actions */}
              <div
                style={{
                  display: 'flex',
                  flexWrap: 'wrap',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  gap: '16px',
                  paddingTop: '8px',
                }}
              >
                <div style={{ fontSize: '0.75rem', color: 'var(--slate-500)', maxWidth: '520px', lineHeight: 1.4 }}>
                  <strong>Educational Note:</strong> {feedbackData.disclaimer}
                </div>

                <div style={{ display: 'flex', gap: '10px' }}>
                  <Button variant="outline" onClick={() => setViewMode('catalog')} icon={<RotateCcw size={14} />}>
                    Practice Another Prompt
                  </Button>
                  <Button variant="primary" onClick={() => navigate('/dashboard')} icon={<ArrowRight size={14} />}>
                    Return to Dashboard
                  </Button>
                </div>
              </div>
            </>
          ) : null}
        </div>
      )}
    </div>
  );
};
