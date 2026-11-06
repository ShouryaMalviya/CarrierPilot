import React, { useState, useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import {
  CheckCircle2,
  XCircle,
  Clock,
  ArrowRight,
  BookOpen,
  Award,
  Sparkles,
  RefreshCw,
  Check,
  Play,
  RotateCcw,
} from 'lucide-react';
import { useAlert } from '../context/AlertContext';
import { api } from '../services/api';
import {
  PracticeTopicSummary,
  PracticeSession,
  AttemptFeedback,
  TopicMastery,
} from '../types';
import { Card } from '../components/common/Card';
import { Button } from '../components/common/Button';
import { Badge } from '../components/common/Badge';
import { EthicalDisclaimerBanner } from '../components/common/EthicalDisclaimerBanner';

type ViewMode = 'lobby' | 'active_session' | 'session_summary';

export const PracticePage: React.FC = () => {
  const { showAlert } = useAlert();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();

  // Mode state
  const [viewMode, setViewMode] = useState<ViewMode>('lobby');

  // Lobby state
  const [topics, setTopics] = useState<PracticeTopicSummary[]>([]);
  const [selectedTopic, setSelectedTopic] = useState<string>('all');
  const [selectedDifficulty, setSelectedDifficulty] = useState<string>('all');
  const [questionCount, setQuestionCount] = useState<number>(5);
  const [isLoadingLobby, setIsLoadingLobby] = useState<boolean>(true);
  const [masteries, setMasteries] = useState<TopicMastery[]>([]);

  // Active Session state
  const [currentSession, setCurrentSession] = useState<PracticeSession | null>(null);
  const [selectedOption, setSelectedOption] = useState<string | null>(null);
  const [isSubmittingAnswer, setIsSubmittingAnswer] = useState<boolean>(false);
  const [attemptFeedback, setAttemptFeedback] = useState<AttemptFeedback | null>(null);
  const [isAdvancing, setIsAdvancing] = useState<boolean>(false);
  const [questionStartTime, setQuestionStartTime] = useState<number>(Date.now());
  const [elapsedSeconds, setElapsedSeconds] = useState<number>(0);

  // Summary state
  const [sessionResults, setSessionResults] = useState<{
    total: number;
    correct: number;
    topic: string;
  } | null>(null);

  // Load topics and masteries on mount
  const fetchLobbyData = async () => {
    setIsLoadingLobby(true);
    try {
      const [topicsRes, masteryRes] = await Promise.all([
        api.get<PracticeTopicSummary[]>('/practice/topics').catch(() => []),
        api.get<{ items: TopicMastery[] }>('/practice/mastery').catch(() => ({ items: [] })),
      ]);

      setTopics(topicsRes || []);
      setMasteries(masteryRes?.items || []);

      // If URL has ?topic=..., preselect it
      const urlTopic = searchParams.get('topic');
      if (urlTopic && topicsRes.some((t) => t.topic.toLowerCase() === urlTopic.toLowerCase())) {
        setSelectedTopic(urlTopic);
      }
    } catch (err: any) {
      showAlert(err?.message || 'Failed to load practice topics.', 'danger');
    } finally {
      setIsLoadingLobby(false);
    }
  };

  useEffect(() => {
    fetchLobbyData();
  }, []);

  // Timer effect for active question
  useEffect(() => {
    let timer: any = null;
    if (viewMode === 'active_session' && !attemptFeedback) {
      timer = setInterval(() => {
        setElapsedSeconds(Math.floor((Date.now() - questionStartTime) / 1000));
      }, 1000);
    }
    return () => clearInterval(timer);
  }, [viewMode, questionStartTime, attemptFeedback]);

  // Start new diagnostic session
  const handleStartSession = async (useAdaptive = false) => {
    try {
      const payload: any = {
        question_count: questionCount,
      };

      if (!useAdaptive && selectedTopic !== 'all') {
        payload.topic = selectedTopic;
      }
      if (!useAdaptive && selectedDifficulty !== 'all') {
        payload.difficulty = selectedDifficulty;
      }

      const session = await api.post<PracticeSession>('/practice/sessions', payload);

      setCurrentSession(session);
      setSelectedOption(null);
      setAttemptFeedback(null);
      setQuestionStartTime(Date.now());
      setElapsedSeconds(0);
      setViewMode('active_session');
      setSessionResults({
        total: session.total_questions,
        correct: 0,
        topic: session.topic,
      });

      showAlert(
        `Diagnostic session launched: ${session.topic} (${session.total_questions} questions).`,
        'success'
      );
    } catch (err: any) {
      showAlert(err?.data?.error?.message || err?.message || 'Failed to start practice session.', 'danger');
    }
  };

  // Submit answer for active question
  const handleSubmitAnswer = async () => {
    if (!currentSession || !currentSession.current_question || !selectedOption) return;

    setIsSubmittingAnswer(true);
    const duration = Math.max(1, Math.floor((Date.now() - questionStartTime) / 1000));

    try {
      const feedback = await api.post<AttemptFeedback>('/practice/attempts', {
        question_id: currentSession.current_question.id,
        user_answer: selectedOption,
        session_id: currentSession.id,
        duration_seconds: duration,
      });

      setAttemptFeedback(feedback);

      // Track running results
      if (feedback.is_correct && sessionResults) {
        setSessionResults({
          ...sessionResults,
          correct: sessionResults.correct + 1,
        });
      }
    } catch (err: any) {
      showAlert(err?.message || 'Failed to submit answer attempt.', 'danger');
    } finally {
      setIsSubmittingAnswer(false);
    }
  };

  // Advance to next question or complete session
  const handleNextQuestion = async () => {
    if (!currentSession) return;

    setIsAdvancing(true);
    try {
      const updated = await api.post<PracticeSession>(`/practice/sessions/${currentSession.id}/next`);
      setCurrentSession(updated);
      setSelectedOption(null);
      setAttemptFeedback(null);
      setQuestionStartTime(Date.now());
      setElapsedSeconds(0);

      if (updated.status === 'completed' || !updated.current_question) {
        setViewMode('session_summary');
        showAlert('Practice session completed! Mastery scores updated.', 'success');
        fetchLobbyData(); // refresh masteries in background
      }
    } catch (err: any) {
      showAlert(err?.message || 'Failed to advance session.', 'danger');
    } finally {
      setIsAdvancing(false);
    }
  };

  // Abandon session
  const handleAbandonSession = async () => {
    if (!currentSession) return;
    if (!window.confirm('Are you sure you want to exit? Incomplete progress in this session will be closed.')) {
      return;
    }

    try {
      await api.post(`/practice/sessions/${currentSession.id}/abandon`);
      showAlert('Session abandoned.', 'info');
      setViewMode('lobby');
      setCurrentSession(null);
      fetchLobbyData();
    } catch (err: any) {
      showAlert(err?.message || 'Failed to abandon session.', 'danger');
    }
  };

  const formatTimer = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs < 10 ? '0' : ''}${secs}`;
  };

  const getTierVariant = (tier: string): 'success' | 'primary' | 'warning' | 'danger' | 'neutral' => {
    switch (tier) {
      case 'mastered':
        return 'success';
      case 'proficient':
        return 'primary';
      case 'developing':
        return 'warning';
      case 'needs_practice':
        return 'danger';
      default:
        return 'neutral';
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
      <EthicalDisclaimerBanner />

      {/* Header */}
      <div style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', justifyContent: 'space-between', gap: '16px' }}>
        <div>
          <h2 style={{ fontSize: '1.625rem', fontWeight: 800, color: 'var(--slate-900)', margin: 0 }}>
            Diagnostic Practice Room
          </h2>
          <p style={{ color: 'var(--slate-500)', fontSize: '0.875rem', marginTop: '4px', margin: 0 }}>
            Adaptive technical MCQs, progressive prompt delivery, instant objective grading, and exponential decay mastery tracking.
          </p>
        </div>

        {viewMode === 'lobby' && (
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <Button
              variant="outline"
              size="sm"
              onClick={fetchLobbyData}
              isLoading={isLoadingLobby}
              icon={<RefreshCw size={14} className={isLoadingLobby ? 'spin' : ''} />}
            >
              Refresh Bank
            </Button>
          </div>
        )}
      </div>

      {/* ========================================================================= */}
      {/* 1. LOBBY VIEW                                                             */}
      {/* ========================================================================= */}
      {viewMode === 'lobby' && (
        <div style={{ display: 'grid', gridTemplateColumns: '1.3fr 1fr', gap: '24px', alignItems: 'start' }}>
          {/* Left Column: Practice Session Launcher */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
            <Card
              title="Launch Diagnostic Session"
              subtitle="Configure your curriculum focus or launch an adaptive remediation quiz"
            >
              <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
                {/* Topic Selector */}
                <div>
                  <label style={{ display: 'block', fontSize: '0.8125rem', fontWeight: 600, color: 'var(--slate-700)', marginBottom: '8px' }}>
                    Select Curriculum Topic Domain:
                  </label>
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(180px, 1fr))', gap: '10px' }}>
                    <button
                      type="button"
                      onClick={() => setSelectedTopic('all')}
                      style={{
                        padding: '12px 14px',
                        borderRadius: 'var(--radius-md)',
                        border: selectedTopic === 'all' ? '2px solid var(--primary-600)' : '1px solid var(--slate-200)',
                        backgroundColor: selectedTopic === 'all' ? 'var(--primary-50)' : '#ffffff',
                        color: selectedTopic === 'all' ? 'var(--primary-900)' : 'var(--slate-800)',
                        fontWeight: selectedTopic === 'all' ? 700 : 500,
                        fontSize: '0.8125rem',
                        textAlign: 'left',
                        cursor: 'pointer',
                        transition: 'all 0.15s ease',
                      }}
                    >
                      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                        <span>All Topics (Adaptive)</span>
                        {selectedTopic === 'all' && <Check size={16} color="var(--primary-600)" />}
                      </div>
                      <span style={{ fontSize: '0.6875rem', color: 'var(--slate-500)', display: 'block', marginTop: '2px' }}>
                        Multi-domain benchmark
                      </span>
                    </button>

                    {topics.map((t) => {
                      const isSelected = selectedTopic === t.topic;
                      return (
                        <button
                          key={t.topic}
                          type="button"
                          onClick={() => setSelectedTopic(t.topic)}
                          style={{
                            padding: '12px 14px',
                            borderRadius: 'var(--radius-md)',
                            border: isSelected ? '2px solid var(--primary-600)' : '1px solid var(--slate-200)',
                            backgroundColor: isSelected ? 'var(--primary-50)' : '#ffffff',
                            color: isSelected ? 'var(--primary-900)' : 'var(--slate-800)',
                            fontWeight: isSelected ? 700 : 500,
                            fontSize: '0.8125rem',
                            textAlign: 'left',
                            cursor: 'pointer',
                            transition: 'all 0.15s ease',
                          }}
                        >
                          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                            <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                              {t.topic}
                            </span>
                            {isSelected && <Check size={16} color="var(--primary-600)" />}
                          </div>
                          <span style={{ fontSize: '0.6875rem', color: 'var(--slate-500)', display: 'block', marginTop: '2px' }}>
                            {t.total_questions} questions available
                          </span>
                        </button>
                      );
                    })}
                  </div>
                </div>

                {/* Difficulty & Count */}
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
                  <div>
                    <label style={{ display: 'block', fontSize: '0.8125rem', fontWeight: 600, color: 'var(--slate-700)', marginBottom: '6px' }}>
                      Target Difficulty:
                    </label>
                    <select
                      className="input"
                      value={selectedDifficulty}
                      onChange={(e) => setSelectedDifficulty(e.target.value)}
                    >
                      <option value="all">Adaptive (All Levels)</option>
                      <option value="easy">Easy (Fundamentals)</option>
                      <option value="medium">Medium (Core Application)</option>
                      <option value="hard">Hard (Advanced / Edge Cases)</option>
                    </select>
                  </div>

                  <div>
                    <label style={{ display: 'block', fontSize: '0.8125rem', fontWeight: 600, color: 'var(--slate-700)', marginBottom: '6px' }}>
                      Session Length:
                    </label>
                    <select
                      className="input"
                      value={questionCount}
                      onChange={(e) => setQuestionCount(Number(e.target.value))}
                    >
                      <option value={3}>3 Questions (Micro-quiz)</option>
                      <option value={5}>5 Questions (Standard Diagnostic)</option>
                      <option value={10}>10 Questions (Comprehensive Check)</option>
                    </select>
                  </div>
                </div>

                {/* Action Buttons */}
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '12px', paddingTop: '8px' }}>
                  <Button
                    variant="primary"
                    onClick={() => handleStartSession(false)}
                    icon={<Play size={16} />}
                  >
                    Start Selected Session
                  </Button>

                  <Button
                    variant="secondary"
                    onClick={() => handleStartSession(true)}
                    icon={<Sparkles size={16} />}
                  >
                    Start Adaptive Remediation Session
                  </Button>
                </div>
              </div>
            </Card>
          </div>

          {/* Right Column: Topic Mastery Overview */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
            <Card
              title="Curriculum Mastery Diagnostics"
              subtitle="Exponential decay mastery scores (γ=0.85) updated after each graded attempt"
            >
              {masteries.length === 0 ? (
                <div style={{ padding: '32px 16px', textAlign: 'center', color: 'var(--slate-500)' }}>
                  <BookOpen size={32} color="var(--slate-300)" style={{ margin: '0 auto 8px' }} />
                  <p style={{ margin: 0, fontWeight: 500 }}>No topic mastery records yet.</p>
                  <p style={{ margin: '4px 0 0', fontSize: '0.75rem' }}>
                    Complete practice sessions to calibrate your individual mastery indices.
                  </p>
                </div>
              ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                  {masteries.map((m) => (
                    <div
                      key={m.topic}
                      style={{
                        padding: '12px 14px',
                        backgroundColor: 'var(--slate-50)',
                        borderRadius: 'var(--radius-md)',
                        border: '1px solid var(--slate-200)',
                      }}
                    >
                      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '6px' }}>
                        <span style={{ fontSize: '0.875rem', fontWeight: 700, color: 'var(--slate-800)' }}>
                          {m.topic}
                        </span>
                        <Badge variant={getTierVariant(m.status_tier)}>
                          {m.status_tier.replace('_', ' ')}
                        </Badge>
                      </div>

                      <div style={{ marginBottom: '6px' }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', color: 'var(--slate-500)', marginBottom: '2px' }}>
                          <span>Mastery Index</span>
                          <strong>{m.mastery_score.toFixed(0)}%</strong>
                        </div>
                        <div style={{ height: '5px', backgroundColor: 'var(--slate-200)', borderRadius: '3px', overflow: 'hidden' }}>
                          <div
                            style={{
                              height: '100%',
                              width: `${Math.min(100, Math.max(0, m.mastery_score))}%`,
                              backgroundColor:
                                m.status_tier === 'mastered'
                                  ? 'var(--success-600)'
                                  : m.status_tier === 'proficient'
                                  ? 'var(--primary-600)'
                                  : m.status_tier === 'developing'
                                  ? 'var(--warning-500)'
                                  : 'var(--danger-500)',
                              borderRadius: '3px',
                            }}
                          />
                        </div>
                      </div>

                      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.6875rem', color: 'var(--slate-400)' }}>
                        <span>Accuracy: {(m.accuracy_percentage || 0).toFixed(0)}%</span>
                        <span>{m.recent_attempts_count || 0} attempts</span>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </Card>
          </div>
        </div>
      )}

      {/* ========================================================================= */}
      {/* 2. ACTIVE SESSION VIEW                                                    */}
      {/* ========================================================================= */}
      {viewMode === 'active_session' && currentSession && currentSession.current_question && (
        <div style={{ maxWidth: '820px', margin: '0 auto', width: '100%', display: 'flex', flexDirection: 'column', gap: '20px' }}>
          {/* Top Session Progress Bar */}
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
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <span style={{ fontSize: '0.875rem', fontWeight: 700, color: 'var(--slate-900)' }}>
                Question {currentSession.current_index + 1} of {currentSession.total_questions}
              </span>
              <Badge variant="primary">{currentSession.topic}</Badge>
              <Badge variant="neutral">
                {currentSession.current_question.difficulty.toUpperCase()}
              </Badge>
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.8125rem', color: 'var(--slate-600)', fontWeight: 600 }}>
                <Clock size={16} color="var(--primary-600)" />
                <span>{formatTimer(elapsedSeconds)}</span>
              </div>

              <Button size="sm" variant="outline" onClick={handleAbandonSession}>
                Exit Session
              </Button>
            </div>
          </div>

          {/* Question Prompt Card */}
          <div
            style={{
              padding: '32px',
              backgroundColor: '#ffffff',
              borderRadius: 'var(--radius-xl)',
              boxShadow: 'var(--shadow-md)',
              border: '1px solid var(--slate-200)',
              display: 'flex',
              flexDirection: 'column',
              gap: '24px',
            }}
          >
            <div>
              <span style={{ fontSize: '0.75rem', textTransform: 'uppercase', letterSpacing: '0.06em', color: 'var(--primary-600)', fontWeight: 700 }}>
                Objective Diagnostic Prompt
              </span>
              <h3
                style={{
                  fontSize: '1.25rem',
                  fontWeight: 700,
                  color: 'var(--slate-900)',
                  lineHeight: 1.5,
                  margin: '8px 0 0',
                  whiteSpace: 'pre-wrap',
                }}
              >
                {currentSession.current_question.question_text}
              </h3>
            </div>

            {/* Options List */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
              {currentSession.current_question.options.map((opt) => {
                const isSelected = selectedOption === opt.key;
                const isGraded = attemptFeedback !== null;
                const isCorrectOption = isGraded && attemptFeedback.correct_answer_key === opt.key;
                const isUserWrongOption = isGraded && isSelected && !attemptFeedback.is_correct;

                let border = isSelected ? '2px solid var(--primary-600)' : '1px solid var(--slate-200)';
                let bg = isSelected ? 'var(--primary-50)' : '#ffffff';
                let textColor = isSelected ? 'var(--primary-900)' : 'var(--slate-800)';

                if (isGraded) {
                  if (isCorrectOption) {
                    border = '2px solid var(--success-border)';
                    bg = 'var(--success-bg)';
                    textColor = 'var(--success-text)';
                  } else if (isUserWrongOption) {
                    border = '2px solid var(--danger-border)';
                    bg = 'var(--danger-bg)';
                    textColor = 'var(--danger-text)';
                  } else {
                    bg = 'var(--slate-50)';
                    textColor = 'var(--slate-500)';
                  }
                }

                return (
                  <button
                    key={opt.key}
                    type="button"
                    disabled={isGraded || isSubmittingAnswer}
                    onClick={() => setSelectedOption(opt.key)}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: '14px',
                      padding: '16px 20px',
                      borderRadius: 'var(--radius-lg)',
                      border,
                      backgroundColor: bg,
                      color: textColor,
                      cursor: isGraded ? 'default' : 'pointer',
                      textAlign: 'left',
                      transition: 'all 0.15s ease',
                      fontWeight: isSelected || isCorrectOption ? 600 : 500,
                    }}
                  >
                    <div
                      style={{
                        width: '32px',
                        height: '32px',
                        borderRadius: '8px',
                        backgroundColor: isSelected || isCorrectOption ? 'rgba(79, 70, 229, 0.15)' : 'var(--slate-100)',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        fontWeight: 700,
                        fontSize: '0.875rem',
                        flexShrink: 0,
                      }}
                    >
                      {opt.key}
                    </div>
                    <span style={{ flex: 1, fontSize: '0.9375rem', lineHeight: 1.4 }}>
                      {opt.text}
                    </span>
                    {isGraded && isCorrectOption && <CheckCircle2 size={20} color="var(--success-icon)" />}
                    {isGraded && isUserWrongOption && <XCircle size={20} color="var(--danger-icon)" />}
                  </button>
                );
              })}
            </div>

            {/* Answer Submission Controls */}
            {!attemptFeedback ? (
              <div style={{ display: 'flex', justifyContent: 'flex-end', paddingTop: '8px' }}>
                <Button
                  variant="primary"
                  disabled={!selectedOption || isSubmittingAnswer}
                  isLoading={isSubmittingAnswer}
                  onClick={handleSubmitAnswer}
                  icon={<Check size={16} />}
                >
                  Confirm & Grade Answer
                </Button>
              </div>
            ) : (
              /* Educational Feedback Banner */
              <div
                style={{
                  padding: '20px 24px',
                  borderRadius: 'var(--radius-lg)',
                  backgroundColor: attemptFeedback.is_correct ? 'var(--success-bg)' : 'var(--danger-bg)',
                  border: `1px solid ${attemptFeedback.is_correct ? 'var(--success-border)' : 'var(--danger-border)'}`,
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '12px',
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    {attemptFeedback.is_correct ? (
                      <>
                        <CheckCircle2 size={20} color="var(--success-icon)" />
                        <span style={{ fontWeight: 800, fontSize: '0.9375rem', color: 'var(--success-text)' }}>
                          Correct! +1.0 Score
                        </span>
                      </>
                    ) : (
                      <>
                        <XCircle size={20} color="var(--danger-icon)" />
                        <span style={{ fontWeight: 800, fontSize: '0.9375rem', color: 'var(--danger-text)' }}>
                          Incorrect. Correct Choice is Option {attemptFeedback.correct_answer_key}
                        </span>
                      </>
                    )}
                  </div>

                  <span style={{ fontSize: '0.75rem', color: 'var(--slate-500)' }}>
                    Answered in {attemptFeedback.duration_seconds || elapsedSeconds}s
                  </span>
                </div>

                <div
                  style={{
                    padding: '12px 14px',
                    backgroundColor: '#ffffff',
                    borderRadius: 'var(--radius-md)',
                    border: '1px solid rgba(0, 0, 0, 0.05)',
                    fontSize: '0.8125rem',
                    color: 'var(--slate-800)',
                    lineHeight: 1.5,
                  }}
                >
                  <strong>Pedagogical Explanation:</strong> {attemptFeedback.explanation}
                </div>

                <div style={{ display: 'flex', justifyContent: 'flex-end', paddingTop: '4px' }}>
                  <Button
                    variant="primary"
                    isLoading={isAdvancing}
                    onClick={handleNextQuestion}
                    icon={<ArrowRight size={16} />}
                  >
                    {currentSession.current_index + 1 >= currentSession.total_questions
                      ? 'Complete Session & View Summary'
                      : 'Next Question'}
                  </Button>
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* ========================================================================= */}
      {/* 3. SESSION SUMMARY VIEW                                                   */}
      {/* ========================================================================= */}
      {viewMode === 'session_summary' && sessionResults && (
        <div style={{ maxWidth: '640px', margin: '0 auto', width: '100%' }}>
          <Card>
            <div style={{ textAlign: 'center', padding: '24px 16px' }}>
              <div
                style={{
                  width: '56px',
                  height: '56px',
                  borderRadius: '16px',
                  backgroundColor: 'rgba(16, 185, 129, 0.12)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  margin: '0 auto 16px',
                }}
              >
                <Award size={32} color="var(--success-icon)" />
              </div>

              <h3 style={{ fontSize: '1.5rem', fontWeight: 800, color: 'var(--slate-900)', margin: '0 0 6px' }}>
                Practice Session Completed!
              </h3>
              <p style={{ color: 'var(--slate-500)', fontSize: '0.875rem', margin: '0 0 24px' }}>
                Topic domain: <strong>{sessionResults.topic}</strong>
              </p>

              {/* Score Gauge */}
              <div
                style={{
                  padding: '24px',
                  backgroundColor: 'var(--slate-50)',
                  borderRadius: 'var(--radius-lg)',
                  border: '1px solid var(--slate-200)',
                  marginBottom: '24px',
                }}
              >
                <div style={{ fontSize: '2.5rem', fontWeight: 800, color: 'var(--primary-600)' }}>
                  {sessionResults.total > 0
                    ? `${((sessionResults.correct / sessionResults.total) * 100).toFixed(0)}%`
                    : '100%'}
                </div>
                <p style={{ margin: '4px 0 0', fontWeight: 600, color: 'var(--slate-700)', fontSize: '0.9375rem' }}>
                  {sessionResults.correct} out of {sessionResults.total} questions correct
                </p>
                <p style={{ margin: '8px 0 0', fontSize: '0.75rem', color: 'var(--slate-500)' }}>
                  Recent attempt recency weights (γ=0.85) applied to your composite topic mastery.
                </p>
              </div>

              {/* Actions */}
              <div style={{ display: 'flex', justifyContent: 'center', gap: '12px' }}>
                <Button
                  variant="outline"
                  onClick={() => setViewMode('lobby')}
                  icon={<RotateCcw size={16} />}
                >
                  Start Another Session
                </Button>

                <Button
                  variant="primary"
                  onClick={() => navigate('/dashboard')}
                  icon={<ArrowRight size={16} />}
                >
                  Return to Dashboard
                </Button>
              </div>
            </div>
          </Card>
        </div>
      )}
    </div>
  );
};
