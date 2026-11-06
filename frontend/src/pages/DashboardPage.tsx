import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Flame,
  Award,
  Target,
  Layers,
  ArrowRight,
  CheckCircle2,
  Clock,
  RefreshCw,
  FileUp,
  Briefcase,
  HelpCircle,
  MessageSquare,
  Sparkles,
  AlertCircle,
  ExternalLink,
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { useAlert } from '../context/AlertContext';
import { api } from '../services/api';
import { DashboardProgress, TopicMastery } from '../types';
import { Card } from '../components/common/Card';
import { Button } from '../components/common/Button';
import { Badge } from '../components/common/Badge';
import { EthicalDisclaimerBanner } from '../components/common/EthicalDisclaimerBanner';

export const DashboardPage: React.FC = () => {
  const { profile } = useAuth();
  const { showAlert } = useAlert();
  const navigate = useNavigate();

  const [data, setData] = useState<DashboardProgress | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [isRefreshing, setIsRefreshing] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const fetchDashboardData = async (isManualRefresh = false) => {
    if (isManualRefresh) {
      setIsRefreshing(true);
    } else {
      setIsLoading(true);
    }
    setError(null);

    try {
      const response = await api.get<DashboardProgress>('/progress/dashboard');
      setData(response);
      if (isManualRefresh) {
        showAlert('Dashboard telemetry updated.', 'success');
      }
    } catch (err: any) {
      const msg =
        err?.data?.error?.message ||
        err?.message ||
        'Unable to load candidate progress telemetry.';
      setError(msg);
      showAlert(msg, 'danger');
    } finally {
      setIsLoading(false);
      setIsRefreshing(false);
    }
  };

  useEffect(() => {
    fetchDashboardData();
  }, []);

  const getReadinessBadgeVariant = (level?: string): 'neutral' | 'warning' | 'primary' | 'success' => {
    switch (level) {
      case 'interview_ready':
        return 'success';
      case 'placement_ready':
        return 'primary';
      case 'developing':
        return 'warning';
      default:
        return 'neutral';
    }
  };

  const getTierBadgeVariant = (tier: TopicMastery['status_tier']): 'neutral' | 'warning' | 'primary' | 'success' | 'danger' => {
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

  const formatPracticeTime = (seconds: number) => {
    if (!seconds || seconds <= 0) return '0m';
    const mins = Math.floor(seconds / 60);
    if (mins < 60) return `${mins}m`;
    const hours = (mins / 60).toFixed(1);
    return `${hours}h`;
  };

  const getActionTargetUrl = (actionType: string, serverUrl?: string | null): string => {
    if (serverUrl && serverUrl.startsWith('/')) return serverUrl;
    switch (actionType) {
      case 'upload_resume':
        return '/resumes';
      case 'start_practice':
      case 'remediate_weak_topic':
      case 'advance_challenge':
        return '/practice';
      case 'mock_interview':
        return '/interviews';
      case 'explore_jobs':
        return '/matching';
      default:
        return '/practice';
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
      <EthicalDisclaimerBanner />

      {/* Header Bar */}
      <div
        style={{
          display: 'flex',
          flexWrap: 'wrap',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: '16px',
        }}
      >
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <h2 style={{ fontSize: '1.625rem', fontWeight: 800, color: 'var(--slate-900)', margin: 0 }}>
              Placement Intelligence Dashboard
            </h2>
            <Badge variant="primary">
              {data?.target_role || profile?.target_role || 'Junior Python Developer'}
            </Badge>
          </div>
          <p style={{ color: 'var(--slate-500)', fontSize: '0.875rem', marginTop: '4px', margin: 0 }}>
            Real-time readiness telemetry, daily practice habits, and topic mastery diagnostics.
          </p>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <Button
            variant="outline"
            size="sm"
            onClick={() => navigate('/onboarding')}
            icon={<ExternalLink size={14} />}
          >
            Configure Role
          </Button>

          <Button
            variant="secondary"
            size="sm"
            isLoading={isRefreshing}
            onClick={() => fetchDashboardData(true)}
            icon={<RefreshCw size={14} className={isRefreshing ? 'spin' : ''} />}
          >
            Refresh Telemetry
          </Button>
        </div>
      </div>

      {/* Loading Skeleton */}
      {isLoading && !data && (
        <div
          style={{
            padding: '60px 20px',
            textAlign: 'center',
            backgroundColor: '#ffffff',
            borderRadius: 'var(--radius-lg)',
            border: '1px solid var(--slate-200)',
          }}
        >
          <div
            style={{
              width: '40px',
              height: '40px',
              border: '3px solid var(--slate-200)',
              borderTopColor: 'var(--primary-600)',
              borderRadius: '50%',
              margin: '0 auto 16px',
              animation: 'spin 0.8s linear infinite',
            }}
          />
          <p style={{ color: 'var(--slate-600)', fontSize: '0.9375rem', fontWeight: 500 }}>
            Computing multi-factor placement readiness index...
          </p>
        </div>
      )}

      {/* Error Fallback */}
      {error && !isLoading && (
        <div
          style={{
            padding: '24px',
            backgroundColor: 'var(--danger-50)',
            border: '1px solid var(--danger-200)',
            borderRadius: 'var(--radius-lg)',
            display: 'flex',
            alignItems: 'flex-start',
            gap: '12px',
          }}
        >
          <AlertCircle size={20} color="var(--danger-600)" style={{ flexShrink: 0, marginTop: '2px' }} />
          <div style={{ flex: 1 }}>
            <h4 style={{ margin: '0 0 4px', color: 'var(--danger-900)', fontSize: '0.9375rem' }}>
              Telemetry Synchronization Error
            </h4>
            <p style={{ margin: '0 0 12px', color: 'var(--danger-700)', fontSize: '0.8125rem' }}>
              {error}
            </p>
            <Button size="sm" variant="danger" onClick={() => fetchDashboardData(false)}>
              Retry Loading
            </Button>
          </div>
        </div>
      )}

      {/* Loaded Dashboard Content */}
      {data && (
        <>
          {/* Top 4 Key Metric Stats */}
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))',
              gap: '16px',
            }}
          >
            {/* 1. Practice Streak */}
            <Card>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <span style={{ fontSize: '0.8125rem', fontWeight: 600, color: 'var(--slate-500)' }}>
                  Daily Streak
                </span>
                <div
                  style={{
                    width: '32px',
                    height: '32px',
                    borderRadius: '8px',
                    backgroundColor: 'rgba(249, 115, 22, 0.12)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                  }}
                >
                  <Flame size={18} color="#ea580c" />
                </div>
              </div>
              <div style={{ marginTop: '12px', display: 'flex', alignItems: 'baseline', gap: '8px' }}>
                <span style={{ fontSize: '2rem', fontWeight: 800, color: 'var(--slate-900)' }}>
                  {data.streak_days}
                </span>
                <span style={{ fontSize: '0.875rem', color: 'var(--slate-500)', fontWeight: 500 }}>
                  days active
                </span>
              </div>
              <div
                style={{
                  marginTop: '12px',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px',
                  fontSize: '0.75rem',
                  color: 'var(--slate-500)',
                }}
              >
                <Award size={14} color="var(--primary-600)" />
                <span>
                  All-time record: <strong>{data.longest_streak_days} days</strong>
                </span>
              </div>
            </Card>

            {/* 2. Composite Placement Readiness */}
            <Card>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <span style={{ fontSize: '0.8125rem', fontWeight: 600, color: 'var(--slate-500)' }}>
                  Readiness Index
                </span>
                <Badge variant={getReadinessBadgeVariant(data.readiness.readiness_level)}>
                  {data.readiness.readiness_level.replace('_', ' ').toUpperCase()}
                </Badge>
              </div>
              <div style={{ marginTop: '12px', display: 'flex', alignItems: 'baseline', gap: '8px' }}>
                <span
                  style={{
                    fontSize: '2rem',
                    fontWeight: 800,
                    color:
                      data.readiness.overall_readiness_score >= 70
                        ? 'var(--success-600)'
                        : data.readiness.overall_readiness_score >= 40
                        ? 'var(--primary-600)'
                        : 'var(--warning-600)',
                  }}
                >
                  {data.readiness.overall_readiness_score.toFixed(0)}%
                </span>
                <span style={{ fontSize: '0.875rem', color: 'var(--slate-500)' }}>
                  composite score
                </span>
              </div>
              <div style={{ marginTop: '12px' }}>
                <div
                  style={{
                    height: '6px',
                    width: '100%',
                    backgroundColor: 'var(--slate-100)',
                    borderRadius: '3px',
                    overflow: 'hidden',
                  }}
                >
                  <div
                    style={{
                      height: '100%',
                      width: `${Math.min(100, Math.max(0, data.readiness.overall_readiness_score))}%`,
                      backgroundColor:
                        data.readiness.overall_readiness_score >= 70
                          ? 'var(--success-600)'
                          : 'var(--primary-600)',
                      borderRadius: '3px',
                    }}
                  />
                </div>
              </div>
            </Card>

            {/* 3. Diagnostic Accuracy */}
            <Card>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <span style={{ fontSize: '0.8125rem', fontWeight: 600, color: 'var(--slate-500)' }}>
                  Diagnostic Accuracy
                </span>
                <div
                  style={{
                    width: '32px',
                    height: '32px',
                    borderRadius: '8px',
                    backgroundColor: 'rgba(37, 99, 235, 0.1)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                  }}
                >
                  <Target size={18} color="var(--primary-600)" />
                </div>
              </div>
              <div style={{ marginTop: '12px', display: 'flex', alignItems: 'baseline', gap: '8px' }}>
                <span style={{ fontSize: '2rem', fontWeight: 800, color: 'var(--slate-900)' }}>
                  {data.overall_accuracy_percentage.toFixed(1)}%
                </span>
                <span style={{ fontSize: '0.875rem', color: 'var(--slate-500)' }}>
                  ({data.correct_attempts}/{data.total_attempts} correct)
                </span>
              </div>
              <div
                style={{
                  marginTop: '12px',
                  fontSize: '0.75rem',
                  color: 'var(--slate-500)',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px',
                }}
              >
                <Clock size={14} />
                <span>Practice time: <strong>{formatPracticeTime(data.total_practice_time_seconds)}</strong></span>
              </div>
            </Card>

            {/* 4. Practice Sessions */}
            <Card>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <span style={{ fontSize: '0.8125rem', fontWeight: 600, color: 'var(--slate-500)' }}>
                  Sessions Completed
                </span>
                <div
                  style={{
                    width: '32px',
                    height: '32px',
                    borderRadius: '8px',
                    backgroundColor: 'rgba(16, 185, 129, 0.1)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                  }}
                >
                  <Layers size={18} color="var(--success-600)" />
                </div>
              </div>
              <div style={{ marginTop: '12px', display: 'flex', alignItems: 'baseline', gap: '8px' }}>
                <span style={{ fontSize: '2rem', fontWeight: 800, color: 'var(--slate-900)' }}>
                  {data.completed_sessions_count}
                </span>
                <span style={{ fontSize: '0.875rem', color: 'var(--slate-500)' }}>
                  sessions
                </span>
              </div>
              <div
                style={{
                  marginTop: '12px',
                  fontSize: '0.75rem',
                  color: 'var(--slate-500)',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px',
                }}
              >
                <CheckCircle2 size={14} color="var(--success-600)" />
                <span>
                  {data.active_sessions_count > 0
                    ? `${data.active_sessions_count} session currently in progress`
                    : 'All practice sessions completed'}
                </span>
              </div>
            </Card>
          </div>

          {/* Next Recommended Action Banner */}
          {data.next_action && (
            <div
              style={{
                background: 'linear-gradient(135deg, var(--primary-800), var(--primary-900))',
                borderRadius: 'var(--radius-xl)',
                padding: '24px 28px',
                color: '#ffffff',
                boxShadow: 'var(--shadow-md)',
                display: 'flex',
                flexWrap: 'wrap',
                alignItems: 'center',
                justifyContent: 'space-between',
                gap: '20px',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'flex-start', gap: '16px', maxWidth: '640px' }}>
                <div
                  style={{
                    width: '44px',
                    height: '44px',
                    borderRadius: '12px',
                    backgroundColor: 'rgba(255, 255, 255, 0.15)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    flexShrink: 0,
                  }}
                >
                  <Sparkles size={24} color="#ffffff" />
                </div>
                <div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
                    <span
                      style={{
                        fontSize: '0.75rem',
                        textTransform: 'uppercase',
                        letterSpacing: '0.06em',
                        opacity: 0.85,
                        fontWeight: 700,
                      }}
                    >
                      Adaptive Study Recommendation
                    </span>
                    {data.next_action.target_topic && (
                      <Badge variant="primary" style={{ backgroundColor: 'rgba(255, 255, 255, 0.2)', color: '#ffffff' }}>
                        {data.next_action.target_topic}
                      </Badge>
                    )}
                  </div>
                  <h3 style={{ fontSize: '1.25rem', fontWeight: 700, margin: '0 0 6px', color: '#ffffff' }}>
                    {data.next_action.title}
                  </h3>
                  <p style={{ margin: 0, fontSize: '0.875rem', opacity: 0.9, lineHeight: 1.5 }}>
                    {data.next_action.description}
                  </p>
                </div>
              </div>

              <Button
                variant="primary"
                onClick={() =>
                  navigate(getActionTargetUrl(data.next_action.action_type, data.next_action.target_url))
                }
                style={{
                  backgroundColor: '#ffffff',
                  color: 'var(--primary-800)',
                  fontWeight: 700,
                  boxShadow: '0 4px 12px rgba(0, 0, 0, 0.15)',
                }}
                icon={<ArrowRight size={16} />}
              >
                Take Recommended Action
              </Button>
            </div>
          )}

          {/* Middle Section: Readiness Breakdown & Quick Launch Grid */}
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fit, minmax(360px, 1fr))',
              gap: '24px',
            }}
          >
            {/* Explainable Readiness Breakdown */}
            <Card
              title="Readiness Breakdown"
              subtitle="Explainable component factor scores calibrated for placement readiness"
            >
              <div style={{ display: 'flex', flexDirection: 'column', gap: '16px', marginTop: '8px' }}>
                {/* 1. Resume Coverage */}
                <div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.8125rem', marginBottom: '6px' }}>
                    <span style={{ fontWeight: 600, color: 'var(--slate-700)' }}>
                      Profile & Resume Evidence
                    </span>
                    <span style={{ fontWeight: 700, color: 'var(--slate-900)' }}>
                      {data.readiness.profile_resume_score.toFixed(0)}%
                    </span>
                  </div>
                  <div
                    style={{
                      height: '8px',
                      backgroundColor: 'var(--slate-100)',
                      borderRadius: '4px',
                      overflow: 'hidden',
                    }}
                  >
                    <div
                      style={{
                        height: '100%',
                        width: `${Math.min(100, Math.max(0, data.readiness.profile_resume_score))}%`,
                        backgroundColor: 'var(--primary-600)',
                        borderRadius: '4px',
                      }}
                    />
                  </div>
                </div>

                {/* 2. Practice Mastery */}
                <div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.8125rem', marginBottom: '6px' }}>
                    <span style={{ fontWeight: 600, color: 'var(--slate-700)' }}>
                      Diagnostic Practice Mastery
                    </span>
                    <span style={{ fontWeight: 700, color: 'var(--slate-900)' }}>
                      {data.readiness.practice_mastery_score.toFixed(0)}%
                    </span>
                  </div>
                  <div
                    style={{
                      height: '8px',
                      backgroundColor: 'var(--slate-100)',
                      borderRadius: '4px',
                      overflow: 'hidden',
                    }}
                  >
                    <div
                      style={{
                        height: '100%',
                        width: `${Math.min(100, Math.max(0, data.readiness.practice_mastery_score))}%`,
                        backgroundColor: 'var(--success-600)',
                        borderRadius: '4px',
                      }}
                    />
                  </div>
                </div>

                {/* 3. Job Alignment */}
                <div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.8125rem', marginBottom: '6px' }}>
                    <span style={{ fontWeight: 600, color: 'var(--slate-700)' }}>
                      Job Market Requirement Match
                    </span>
                    <span style={{ fontWeight: 700, color: 'var(--slate-900)' }}>
                      {data.readiness.job_matching_score.toFixed(0)}%
                    </span>
                  </div>
                  <div
                    style={{
                      height: '8px',
                      backgroundColor: 'var(--slate-100)',
                      borderRadius: '4px',
                      overflow: 'hidden',
                    }}
                  >
                    <div
                      style={{
                        height: '100%',
                        width: `${Math.min(100, Math.max(0, data.readiness.job_matching_score))}%`,
                        backgroundColor: '#6366f1',
                        borderRadius: '4px',
                      }}
                    />
                  </div>
                </div>

                {/* 4. Mock Interview Rubric */}
                <div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.8125rem', marginBottom: '6px' }}>
                    <span style={{ fontWeight: 600, color: 'var(--slate-700)' }}>
                      Mock Interview Rubric Performance
                    </span>
                    <span style={{ fontWeight: 700, color: 'var(--slate-900)' }}>
                      {data.readiness.mock_interview_score.toFixed(0)}%
                    </span>
                  </div>
                  <div
                    style={{
                      height: '8px',
                      backgroundColor: 'var(--slate-100)',
                      borderRadius: '4px',
                      overflow: 'hidden',
                    }}
                  >
                    <div
                      style={{
                        height: '100%',
                        width: `${Math.min(100, Math.max(0, data.readiness.mock_interview_score))}%`,
                        backgroundColor: '#ec4899',
                        borderRadius: '4px',
                      }}
                    />
                  </div>
                </div>

                {/* Explanatory Disclaimer Footnote */}
                <div
                  style={{
                    marginTop: '8px',
                    padding: '12px',
                    borderRadius: 'var(--radius-md)',
                    backgroundColor: 'var(--slate-50)',
                    border: '1px solid var(--slate-200)',
                    fontSize: '0.75rem',
                    color: 'var(--slate-500)',
                    lineHeight: 1.45,
                  }}
                >
                  <strong>Assessment Note:</strong> {data.readiness.disclaimer}
                </div>
              </div>
            </Card>

            {/* Quick Workspace Shortcuts */}
            <Card
              title="CareerPrep Workspaces"
              subtitle="Directly jump into your placement preparation tools"
            >
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                <button
                  type="button"
                  onClick={() => navigate('/resumes')}
                  style={{
                    display: 'flex',
                    flexDirection: 'column',
                    alignItems: 'flex-start',
                    padding: '16px',
                    borderRadius: 'var(--radius-md)',
                    border: '1px solid var(--slate-200)',
                    backgroundColor: '#ffffff',
                    cursor: 'pointer',
                    textAlign: 'left',
                    transition: 'var(--transition-fast)',
                  }}
                >
                  <div
                    style={{
                      width: '36px',
                      height: '36px',
                      borderRadius: '8px',
                      backgroundColor: 'var(--primary-50)',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      color: 'var(--primary-600)',
                      marginBottom: '10px',
                    }}
                  >
                    <FileUp size={20} />
                  </div>
                  <span style={{ fontSize: '0.875rem', fontWeight: 600, color: 'var(--slate-800)' }}>
                    Resume Studio
                  </span>
                  <span style={{ fontSize: '0.75rem', color: 'var(--slate-500)', marginTop: '2px' }}>
                    Upload & parse skills
                  </span>
                </button>

                <button
                  type="button"
                  onClick={() => navigate('/matching')}
                  style={{
                    display: 'flex',
                    flexDirection: 'column',
                    alignItems: 'flex-start',
                    padding: '16px',
                    borderRadius: 'var(--radius-md)',
                    border: '1px solid var(--slate-200)',
                    backgroundColor: '#ffffff',
                    cursor: 'pointer',
                    textAlign: 'left',
                    transition: 'var(--transition-fast)',
                  }}
                >
                  <div
                    style={{
                      width: '36px',
                      height: '36px',
                      borderRadius: '8px',
                      backgroundColor: 'rgba(99, 102, 241, 0.1)',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      color: '#6366f1',
                      marginBottom: '10px',
                    }}
                  >
                    <Briefcase size={20} />
                  </div>
                  <span style={{ fontSize: '0.875rem', fontWeight: 600, color: 'var(--slate-800)' }}>
                    Job Matching
                  </span>
                  <span style={{ fontSize: '0.75rem', color: 'var(--slate-500)', marginTop: '2px' }}>
                    Skill coverage gaps
                  </span>
                </button>

                <button
                  type="button"
                  onClick={() => navigate('/practice')}
                  style={{
                    display: 'flex',
                    flexDirection: 'column',
                    alignItems: 'flex-start',
                    padding: '16px',
                    borderRadius: 'var(--radius-md)',
                    border: '1px solid var(--slate-200)',
                    backgroundColor: '#ffffff',
                    cursor: 'pointer',
                    textAlign: 'left',
                    transition: 'var(--transition-fast)',
                  }}
                >
                  <div
                    style={{
                      width: '36px',
                      height: '36px',
                      borderRadius: '8px',
                      backgroundColor: 'rgba(16, 185, 129, 0.1)',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      color: 'var(--success-600)',
                      marginBottom: '10px',
                    }}
                  >
                    <HelpCircle size={20} />
                  </div>
                  <span style={{ fontSize: '0.875rem', fontWeight: 600, color: 'var(--slate-800)' }}>
                    Diagnostic MCQs
                  </span>
                  <span style={{ fontSize: '0.75rem', color: 'var(--slate-500)', marginTop: '2px' }}>
                    Adaptive practice room
                  </span>
                </button>

                <button
                  type="button"
                  onClick={() => navigate('/interviews')}
                  style={{
                    display: 'flex',
                    flexDirection: 'column',
                    alignItems: 'flex-start',
                    padding: '16px',
                    borderRadius: 'var(--radius-md)',
                    border: '1px solid var(--slate-200)',
                    backgroundColor: '#ffffff',
                    cursor: 'pointer',
                    textAlign: 'left',
                    transition: 'var(--transition-fast)',
                  }}
                >
                  <div
                    style={{
                      width: '36px',
                      height: '36px',
                      borderRadius: '8px',
                      backgroundColor: 'rgba(236, 72, 153, 0.1)',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      color: '#ec4899',
                      marginBottom: '10px',
                    }}
                  >
                    <MessageSquare size={20} />
                  </div>
                  <span style={{ fontSize: '0.875rem', fontWeight: 600, color: 'var(--slate-800)' }}>
                    Mock Interviews
                  </span>
                  <span style={{ fontSize: '0.75rem', color: 'var(--slate-500)', marginTop: '2px' }}>
                    Typed rubric coaching
                  </span>
                </button>
              </div>
            </Card>
          </div>

          {/* Topic Mastery Progression */}
          <Card
            title="Topic Mastery Progression"
            subtitle="Curriculum competencies ranked by recent-weighted mastery with exponential decay (γ=0.85)"
          >
            {data.topic_masteries.length === 0 ? (
              <div style={{ padding: '32px', textAlign: 'center', color: 'var(--slate-500)' }}>
                No topic attempts recorded yet. Start a diagnostic practice session to track mastery.
              </div>
            ) : (
              <div
                style={{
                  display: 'grid',
                  gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))',
                  gap: '16px',
                }}
              >
                {data.topic_masteries.map((topic) => (
                  <div
                    key={topic.topic}
                    style={{
                      padding: '16px',
                      borderRadius: 'var(--radius-md)',
                      border: '1px solid var(--slate-200)',
                      backgroundColor: 'var(--slate-50)',
                      display: 'flex',
                      flexDirection: 'column',
                      justifyContent: 'space-between',
                      gap: '12px',
                    }}
                  >
                    <div>
                      <div
                        style={{
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'space-between',
                          gap: '8px',
                          marginBottom: '8px',
                        }}
                      >
                        <span style={{ fontSize: '0.9375rem', fontWeight: 700, color: 'var(--slate-800)' }}>
                          {topic.topic}
                        </span>
                        <Badge variant={getTierBadgeVariant(topic.status_tier)}>
                          {topic.status_tier.replace('_', ' ')}
                        </Badge>
                      </div>

                      {/* Mastery Progress Bar */}
                      <div style={{ marginBottom: '8px' }}>
                        <div
                          style={{
                            display: 'flex',
                            justifyContent: 'space-between',
                            fontSize: '0.75rem',
                            color: 'var(--slate-500)',
                            marginBottom: '4px',
                          }}
                        >
                          <span>Mastery Score</span>
                          <span style={{ fontWeight: 700, color: 'var(--slate-800)' }}>
                            {topic.mastery_score.toFixed(0)}%
                          </span>
                        </div>
                        <div
                          style={{
                            height: '6px',
                            backgroundColor: 'var(--slate-200)',
                            borderRadius: '3px',
                            overflow: 'hidden',
                          }}
                        >
                          <div
                            style={{
                              height: '100%',
                              width: `${Math.min(100, Math.max(0, topic.mastery_score))}%`,
                              backgroundColor:
                                topic.status_tier === 'mastered'
                                  ? 'var(--success-600)'
                                  : topic.status_tier === 'proficient'
                                  ? 'var(--primary-600)'
                                  : topic.status_tier === 'developing'
                                  ? 'var(--warning-500)'
                                  : topic.status_tier === 'needs_practice'
                                  ? 'var(--danger-500)'
                                  : 'var(--slate-400)',
                              borderRadius: '3px',
                            }}
                          />
                        </div>
                      </div>

                      <div
                        style={{
                          fontSize: '0.75rem',
                          color: 'var(--slate-500)',
                          display: 'flex',
                          justifyContent: 'space-between',
                        }}
                      >
                        <span>Accuracy: <strong>{topic.accuracy_percentage.toFixed(0)}%</strong></span>
                        <span>Attempts: <strong>{topic.recent_attempts_count}</strong></span>
                      </div>
                    </div>

                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => navigate('/practice')}
                      style={{ width: '100%', justifyContent: 'center' }}
                    >
                      Practice Topic
                    </Button>
                  </div>
                ))}
              </div>
            )}
          </Card>

          {/* 14-Day Activity Telemetry Timeline */}
          <Card
            title="14-Day Practice Activity Telemetry"
            subtitle="Daily question volume and correct attempt trends"
          >
            {data.activity_timeline.length === 0 ? (
              <div style={{ padding: '24px', textAlign: 'center', color: 'var(--slate-500)' }}>
                No recent activity recorded in the past 14 days.
              </div>
            ) : (
              <div>
                <div
                  style={{
                    display: 'grid',
                    gridTemplateColumns: `repeat(${data.activity_timeline.length}, 1fr)`,
                    gap: '8px',
                    alignItems: 'end',
                    height: '140px',
                    padding: '16px 0 8px',
                    borderBottom: '1px solid var(--slate-200)',
                  }}
                >
                  {data.activity_timeline.map((day) => {
                    const maxAttempts = Math.max(
                      ...data.activity_timeline.map((d) => d.attempt_count),
                      5
                    );
                    const barHeightPercent = (day.attempt_count / maxAttempts) * 100;
                    const correctPercent =
                      day.attempt_count > 0 ? (day.correct_count / day.attempt_count) * 100 : 0;

                    return (
                      <div
                        key={day.date}
                        style={{
                          display: 'flex',
                          flexDirection: 'column',
                          alignItems: 'center',
                          height: '100%',
                          justifyContent: 'flex-end',
                        }}
                        title={`${day.date}: ${day.attempt_count} attempts (${day.correct_count} correct)`}
                      >
                        <div
                          style={{
                            width: '100%',
                            maxWidth: '32px',
                            height: `${Math.max(barHeightPercent, 4)}%`,
                            backgroundColor:
                              day.attempt_count === 0
                                ? 'var(--slate-100)'
                                : 'var(--primary-600)',
                            borderRadius: '4px 4px 0 0',
                            position: 'relative',
                            transition: 'height 0.3s ease',
                          }}
                        >
                          {day.attempt_count > 0 && correctPercent > 0 && (
                            <div
                              style={{
                                position: 'absolute',
                                bottom: 0,
                                left: 0,
                                right: 0,
                                height: `${correctPercent}%`,
                                backgroundColor: 'var(--success-500)',
                                borderRadius: '0 0 0 0',
                              }}
                            />
                          )}
                        </div>
                      </div>
                    );
                  })}
                </div>

                {/* Date Labels */}
                <div
                  style={{
                    display: 'grid',
                    gridTemplateColumns: `repeat(${data.activity_timeline.length}, 1fr)`,
                    gap: '8px',
                    paddingTop: '8px',
                    textAlign: 'center',
                  }}
                >
                  {data.activity_timeline.map((day) => {
                    const parts = day.date.split('-');
                    const label = parts.length === 3 ? `${parts[1]}/${parts[2]}` : day.date;
                    return (
                      <span
                        key={day.date}
                        style={{
                          fontSize: '0.6875rem',
                          color: 'var(--slate-400)',
                          overflow: 'hidden',
                          textOverflow: 'ellipsis',
                          whiteSpace: 'nowrap',
                        }}
                      >
                        {label}
                      </span>
                    );
                  })}
                </div>

                {/* Legend */}
                <div
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'flex-end',
                    gap: '16px',
                    marginTop: '16px',
                    fontSize: '0.75rem',
                    color: 'var(--slate-500)',
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                    <div style={{ width: '10px', height: '10px', backgroundColor: 'var(--primary-600)', borderRadius: '2px' }} />
                    <span>Attempts</span>
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                    <div style={{ width: '10px', height: '10px', backgroundColor: 'var(--success-500)', borderRadius: '2px' }} />
                    <span>Correct</span>
                  </div>
                </div>
              </div>
            )}
          </Card>
        </>
      )}
    </div>
  );
};
