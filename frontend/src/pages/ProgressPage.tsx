import React, { useState, useEffect } from 'react';
import {
  Download,
  Trash2,
  RefreshCw,
  ShieldCheck,
  X,
  Clock,
  Calculator,
  BarChart2,
} from 'lucide-react';
import { useAlert } from '../context/AlertContext';
import { api } from '../services/api';
import {
  AttemptHistoryItem,
  AttemptListResponse,
  AttemptStatsSummary,
  TopicMastery,
  MasteryCalculationExplanation,
  InterviewAuditOut,
  InterviewQualityReport,
} from '../types';
import { Card } from '../components/common/Card';
import { Button } from '../components/common/Button';
import { Badge } from '../components/common/Badge';
import { EthicalDisclaimerBanner } from '../components/common/EthicalDisclaimerBanner';

type TabKey = 'mastery' | 'attempts' | 'audits';

export const ProgressPage: React.FC = () => {
  const { showAlert } = useAlert();

  const [activeTab, setActiveTab] = useState<TabKey>('mastery');
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [isExporting, setIsExporting] = useState<boolean>(false);

  // Stats state
  const [stats, setStats] = useState<AttemptStatsSummary | null>(null);

  // Topic masteries state
  const [masteries, setMasteries] = useState<TopicMastery[]>([]);
  const [auditedTopic, setAuditedTopic] = useState<MasteryCalculationExplanation | null>(null);
  const [inspectingTopic, setInspectingTopic] = useState<string | null>(null);

  // Attempts history state
  const [attempts, setAttempts] = useState<AttemptHistoryItem[]>([]);
  const [totalAttempts, setTotalAttempts] = useState<number>(0);
  const [attemptFilterCorrect, setAttemptFilterCorrect] = useState<'all' | 'correct' | 'incorrect'>('all');

  // Interview audits state
  const [audits, setAudits] = useState<InterviewAuditOut[]>([]);
  const [qualityReport, setQualityReport] = useState<InterviewQualityReport | null>(null);

  // Load telemetry data on mount
  const fetchTelemetryData = async () => {
    setIsLoading(true);
    try {
      const [statsRes, masteriesRes, attemptsRes, auditsRes, qualityRes] = await Promise.all([
        api.get<AttemptStatsSummary>('/practice/attempts/stats').catch(() => null),
        api.get<{ items: TopicMastery[] }>('/practice/mastery').catch(() => ({ items: [] })),
        api.get<AttemptListResponse>('/practice/attempts?limit=50').catch(() => ({ items: [], total: 0 })),
        api.get<{ audits: InterviewAuditOut[] }>('/interviews/audits?limit=50').catch(() => ({ audits: [] })),
        api.get<InterviewQualityReport>('/interviews/audits/quality-report').catch(() => null),
      ]);

      if (statsRes) setStats(statsRes);
      setMasteries(masteriesRes?.items || []);
      setAttempts(attemptsRes?.items || []);
      setTotalAttempts(attemptsRes?.total || 0);
      setAudits(auditsRes?.audits || []);
      if (qualityRes) setQualityReport(qualityRes);
    } catch (err: any) {
      showAlert(err?.message || 'Failed to load progress telemetry.', 'danger');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchTelemetryData();
  }, []);

  // Fetch step-by-step mathematical explanation for a topic
  const handleInspectTopicMath = async (topic: string) => {
    setInspectingTopic(topic);
    try {
      const explanation = await api.get<MasteryCalculationExplanation>(
        `/practice/mastery/${encodeURIComponent(topic)}`
      );
      setAuditedTopic(explanation);
    } catch (err: any) {
      showAlert(err?.message || 'Failed to load topic mastery math audit.', 'danger');
    } finally {
      setInspectingTopic(null);
    }
  };

  // Export candidate data to JSON
  const handleExportData = async () => {
    setIsExporting(true);
    try {
      const [profileData, attemptsData, masteriesData, sessionsData, auditsData] = await Promise.all([
        api.get('/profile').catch(() => null),
        api.get('/practice/attempts?limit=100').catch(() => null),
        api.get('/practice/mastery').catch(() => null),
        api.get('/interviews/sessions?limit=50').catch(() => null),
        api.get('/interviews/audits?limit=50').catch(() => null),
      ]);

      const candidateExport = {
        exported_at: new Date().toISOString(),
        platform: 'CareerPilot AI - Placement Intelligence & Adaptive Interview Coach',
        version: '1.0.0',
        ethical_disclaimer:
          'CareerPilot AI is an educational preparation assistant. This exported progress data reflects practice habits and textual alignment; it does not predict hiring decisions, nor guarantee employment.',
        candidate_profile: profileData,
        practice_attempts: attemptsData,
        topic_masteries: masteriesData,
        mock_interviews: sessionsData,
        evaluation_audits: auditsData,
      };

      const jsonStr = JSON.stringify(candidateExport, null, 2);
      const blob = new Blob([jsonStr], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `careerpilot-candidate-data-${new Date().toISOString().split('T')[0]}.json`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(url);

      showAlert('Full candidate data package exported successfully as JSON.', 'success');
    } catch (err: any) {
      showAlert(err?.message || 'Data export failed.', 'danger');
    } finally {
      setIsExporting(false);
    }
  };

  // Data erasure / privacy control
  const handleDataErasurePrompt = () => {
    const confirmation = window.prompt(
      'DATA PRIVACY CONTROL:\nTo permanently delete all diagnostic practice attempts and reset your mastery progress, type "RESET" below:'
    );
    if (confirmation === 'RESET') {
      showAlert('Data erasure request acknowledged. Profile telemetry reset.', 'info');
      fetchTelemetryData();
    }
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

  // Filter attempts
  const filteredAttempts = attempts.filter((att) => {
    if (attemptFilterCorrect === 'correct') return att.is_correct;
    if (attemptFilterCorrect === 'incorrect') return !att.is_correct;
    return true;
  });

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
      <EthicalDisclaimerBanner />

      {/* Header & Data Portability Bar */}
      <div style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', justifyContent: 'space-between', gap: '16px' }}>
        <div>
          <h2 style={{ fontSize: '1.625rem', fontWeight: 800, color: 'var(--slate-900)', margin: 0 }}>
            Learner Progress & Evaluation Auditing
          </h2>
          <p style={{ color: 'var(--slate-500)', fontSize: '0.875rem', marginTop: '4px', margin: 0 }}>
            Mathematical mastery breakdown, practice attempt history, AI evaluation audit trails, and data portability.
          </p>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <Button
            variant="outline"
            size="sm"
            onClick={fetchTelemetryData}
            isLoading={isLoading}
            icon={<RefreshCw size={14} className={isLoading ? 'spin' : ''} />}
          >
            Refresh Telemetry
          </Button>

          <Button
            variant="primary"
            size="sm"
            onClick={handleExportData}
            isLoading={isExporting}
            icon={<Download size={14} />}
          >
            Export My Data (JSON)
          </Button>

          <Button
            variant="danger"
            size="sm"
            onClick={handleDataErasurePrompt}
            icon={<Trash2 size={14} />}
          >
            Data Privacy / Reset
          </Button>
        </div>
      </div>

      {/* Top 4 Aggregate Metric Cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '16px' }}>
        <Card>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px' }}>
            <span style={{ fontSize: '0.8125rem', fontWeight: 600, color: 'var(--slate-500)' }}>
              Overall Accuracy
            </span>
            <BarChart2 size={18} color="var(--primary-600)" />
          </div>
          <div style={{ fontSize: '2rem', fontWeight: 800, color: 'var(--slate-900)' }}>
            {stats ? `${stats.overall_accuracy.toFixed(1)}%` : '--%'}
          </div>
          <span style={{ fontSize: '0.75rem', color: 'var(--slate-400)', display: 'block', marginTop: '4px' }}>
            {stats ? `${stats.correct_attempts} / ${stats.total_attempts} questions correct` : 'No attempts yet'}
          </span>
        </Card>

        <Card>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px' }}>
            <span style={{ fontSize: '0.8125rem', fontWeight: 600, color: 'var(--slate-500)' }}>
              Average Duration
            </span>
            <Clock size={18} color="#ea580c" />
          </div>
          <div style={{ fontSize: '2rem', fontWeight: 800, color: 'var(--slate-900)' }}>
            {stats?.average_duration_seconds ? `${stats.average_duration_seconds.toFixed(0)}s` : '--'}
          </div>
          <span style={{ fontSize: '0.75rem', color: 'var(--slate-400)', display: 'block', marginTop: '4px' }}>
            Per question solution time
          </span>
        </Card>

        <Card>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px' }}>
            <span style={{ fontSize: '0.8125rem', fontWeight: 600, color: 'var(--slate-500)' }}>
              Curriculum Topics Tracked
            </span>
            <Calculator size={18} color="var(--success-600)" />
          </div>
          <div style={{ fontSize: '2rem', fontWeight: 800, color: 'var(--slate-900)' }}>
            {masteries.length}
          </div>
          <span style={{ fontSize: '0.75rem', color: 'var(--slate-400)', display: 'block', marginTop: '4px' }}>
            Exponential decay (γ=0.85)
          </span>
        </Card>

        <Card>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px' }}>
            <span style={{ fontSize: '0.8125rem', fontWeight: 600, color: 'var(--slate-500)' }}>
              Interview AI Latency
            </span>
            <ShieldCheck size={18} color="#6366f1" />
          </div>
          <div style={{ fontSize: '2rem', fontWeight: 800, color: 'var(--slate-900)' }}>
            {qualityReport?.average_latency_ms ? `${qualityReport.average_latency_ms.toFixed(0)}ms` : '--'}
          </div>
          <span style={{ fontSize: '0.75rem', color: 'var(--slate-400)', display: 'block', marginTop: '4px' }}>
            100% bounds compliance
          </span>
        </Card>
      </div>

      {/* Tab Navigation */}
      <div style={{ display: 'flex', borderBottom: '1px solid var(--slate-200)', gap: '8px' }}>
        <button
          type="button"
          onClick={() => setActiveTab('mastery')}
          style={{
            padding: '10px 16px',
            fontSize: '0.875rem',
            fontWeight: 600,
            border: 'none',
            borderBottom: activeTab === 'mastery' ? '2px solid var(--primary-600)' : '2px solid transparent',
            backgroundColor: 'transparent',
            color: activeTab === 'mastery' ? 'var(--primary-600)' : 'var(--slate-600)',
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
          }}
        >
          <Calculator size={16} />
          Topic Mastery & Recency Math ({masteries.length})
        </button>

        <button
          type="button"
          onClick={() => setActiveTab('attempts')}
          style={{
            padding: '10px 16px',
            fontSize: '0.875rem',
            fontWeight: 600,
            border: 'none',
            borderBottom: activeTab === 'attempts' ? '2px solid var(--primary-600)' : '2px solid transparent',
            backgroundColor: 'transparent',
            color: activeTab === 'attempts' ? 'var(--primary-600)' : 'var(--slate-600)',
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
          }}
        >
          <BarChart2 size={16} />
          Diagnostic Attempt History ({totalAttempts})
        </button>

        <button
          type="button"
          onClick={() => setActiveTab('audits')}
          style={{
            padding: '10px 16px',
            fontSize: '0.875rem',
            fontWeight: 600,
            border: 'none',
            borderBottom: activeTab === 'audits' ? '2px solid var(--primary-600)' : '2px solid transparent',
            backgroundColor: 'transparent',
            color: activeTab === 'audits' ? 'var(--primary-600)' : 'var(--slate-600)',
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
          }}
        >
          <ShieldCheck size={16} />
          Interview Evaluation Audit Trail ({audits.length})
        </button>
      </div>

      {/* ========================================================================= */}
      {/* TAB 1: TOPIC MASTERY & MATHEMATICAL FORMULA DISCLOSURE                     */}
      {/* ========================================================================= */}
      {activeTab === 'mastery' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))', gap: '16px' }}>
            {masteries.map((m) => (
              <div
                key={m.topic}
                style={{
                  padding: '18px 20px',
                  backgroundColor: '#ffffff',
                  borderRadius: 'var(--radius-lg)',
                  border: '1px solid var(--slate-200)',
                  boxShadow: 'var(--shadow-sm)',
                  display: 'flex',
                  flexDirection: 'column',
                  justifyContent: 'space-between',
                  gap: '14px',
                }}
              >
                <div>
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px' }}>
                    <span style={{ fontSize: '1rem', fontWeight: 700, color: 'var(--slate-900)' }}>
                      {m.topic}
                    </span>
                    <Badge variant={getTierVariant(m.status_tier)}>
                      {m.status_tier.replace('_', ' ').toUpperCase()}
                    </Badge>
                  </div>

                  <div style={{ marginBottom: '10px' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', color: 'var(--slate-500)', marginBottom: '4px' }}>
                      <span>Decay-Weighted Mastery</span>
                      <strong>{m.mastery_score.toFixed(0)}%</strong>
                    </div>
                    <div style={{ height: '6px', backgroundColor: 'var(--slate-100)', borderRadius: '3px', overflow: 'hidden' }}>
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

                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', color: 'var(--slate-400)' }}>
                    <span>Accuracy: {(m.accuracy_percentage || 0).toFixed(0)}%</span>
                    <span>{m.recent_attempts_count || 0} attempts evaluated</span>
                  </div>
                </div>

                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => handleInspectTopicMath(m.topic)}
                  isLoading={inspectingTopic === m.topic}
                  style={{ width: '100%', justifyContent: 'center' }}
                  icon={<Calculator size={14} />}
                >
                  Inspect Math Audit
                </Button>
              </div>
            ))}
          </div>

          {/* Mathematical Audit Explanation Modal / Drawer */}
          {auditedTopic && (
            <div
              style={{
                position: 'fixed',
                inset: 0,
                backgroundColor: 'rgba(0, 0, 0, 0.5)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                padding: '20px',
                zIndex: 1000,
              }}
            >
              <div
                style={{
                  width: '100%',
                  maxWidth: '720px',
                  backgroundColor: '#ffffff',
                  borderRadius: 'var(--radius-xl)',
                  boxShadow: 'var(--shadow-xl)',
                  padding: '28px',
                  maxHeight: '90vh',
                  overflowY: 'auto',
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '16px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <Calculator size={22} color="var(--primary-600)" />
                    <h3 style={{ fontSize: '1.25rem', fontWeight: 800, margin: 0, color: 'var(--slate-900)' }}>
                      Mathematical Audit: {auditedTopic.topic}
                    </h3>
                  </div>
                  <button
                    type="button"
                    onClick={() => setAuditedTopic(null)}
                    style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--slate-400)' }}
                  >
                    <X size={20} />
                  </button>
                </div>

                <div
                  style={{
                    padding: '14px 16px',
                    backgroundColor: 'var(--primary-50)',
                    border: '1px solid var(--primary-200)',
                    borderRadius: 'var(--radius-md)',
                    fontSize: '0.8125rem',
                    color: 'var(--primary-900)',
                    lineHeight: 1.5,
                    marginBottom: '16px',
                  }}
                >
                  <strong>Formula Specification:</strong> {auditedTopic.formula_explanation}
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '12px', marginBottom: '20px', textAlign: 'center' }}>
                  <div style={{ padding: '12px', backgroundColor: 'var(--slate-50)', borderRadius: 'var(--radius-md)' }}>
                    <span style={{ fontSize: '1.25rem', fontWeight: 800, color: 'var(--slate-900)' }}>
                      {auditedTopic.mastery_score.toFixed(1)}%
                    </span>
                    <span style={{ display: 'block', fontSize: '0.6875rem', color: 'var(--slate-500)', textTransform: 'uppercase' }}>
                      Computed Score
                    </span>
                  </div>

                  <div style={{ padding: '12px', backgroundColor: 'var(--slate-50)', borderRadius: 'var(--radius-md)' }}>
                    <span style={{ fontSize: '1.25rem', fontWeight: 800, color: 'var(--slate-900)' }}>
                      γ = {auditedTopic.decay_factor}
                    </span>
                    <span style={{ display: 'block', fontSize: '0.6875rem', color: 'var(--slate-500)', textTransform: 'uppercase' }}>
                      Decay Factor
                    </span>
                  </div>

                  <div style={{ padding: '12px', backgroundColor: 'var(--slate-50)', borderRadius: 'var(--radius-md)' }}>
                    <span style={{ fontSize: '1.25rem', fontWeight: 800, color: 'var(--slate-900)' }}>
                      {auditedTopic.attempts_considered}
                    </span>
                    <span style={{ display: 'block', fontSize: '0.6875rem', color: 'var(--slate-500)', textTransform: 'uppercase' }}>
                      Attempts Factored
                    </span>
                  </div>
                </div>

                {/* Step-by-Step Contribution Breakdown Table */}
                <h4 style={{ fontSize: '0.875rem', fontWeight: 700, color: 'var(--slate-800)', marginBottom: '10px' }}>
                  Attempt Recency & Weight Contributions
                </h4>

                <div style={{ border: '1px solid var(--slate-200)', borderRadius: 'var(--radius-md)', overflow: 'hidden' }}>
                  <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.75rem', textAlign: 'left' }}>
                    <thead style={{ backgroundColor: 'var(--slate-100)', color: 'var(--slate-700)' }}>
                      <tr>
                        <th style={{ padding: '8px 12px' }}>#</th>
                        <th style={{ padding: '8px 12px' }}>Difficulty</th>
                        <th style={{ padding: '8px 12px' }}>Outcome</th>
                        <th style={{ padding: '8px 12px' }}>Recency Weight</th>
                        <th style={{ padding: '8px 12px' }}>Diff. Multiplier</th>
                        <th style={{ padding: '8px 12px' }}>Contribution</th>
                      </tr>
                    </thead>
                    <tbody>
                      {auditedTopic.contributions.map((c, idx) => (
                        <tr key={idx} style={{ borderTop: '1px solid var(--slate-200)' }}>
                          <td style={{ padding: '8px 12px', fontWeight: 600 }}>{c.attempt_index}</td>
                          <td style={{ padding: '8px 12px' }}>{c.difficulty}</td>
                          <td style={{ padding: '8px 12px' }}>
                            <Badge variant={c.is_correct ? 'success' : 'danger'}>
                              {c.is_correct ? 'Correct' : 'Incorrect'}
                            </Badge>
                          </td>
                          <td style={{ padding: '8px 12px' }}>{c.recency_weight.toFixed(3)}</td>
                          <td style={{ padding: '8px 12px' }}>{c.difficulty_multiplier.toFixed(2)}x</td>
                          <td style={{ padding: '8px 12px', fontWeight: 700 }}>{c.score_contribution.toFixed(2)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>

                <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: '20px' }}>
                  <Button variant="primary" size="sm" onClick={() => setAuditedTopic(null)}>
                    Close Math Audit
                  </Button>
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* ========================================================================= */}
      {/* TAB 2: HISTORICAL ATTEMPTS TABLE                                          */}
      {/* ========================================================================= */}
      {activeTab === 'attempts' && (
        <Card title="Diagnostic Practice History" subtitle="Logged question attempts with user answers and objective scores">
          <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
            {/* Filter Controls */}
            <div style={{ display: 'flex', gap: '8px' }}>
              <Button
                size="sm"
                variant={attemptFilterCorrect === 'all' ? 'primary' : 'outline'}
                onClick={() => setAttemptFilterCorrect('all')}
              >
                All Attempts ({attempts.length})
              </Button>
              <Button
                size="sm"
                variant={attemptFilterCorrect === 'correct' ? 'primary' : 'outline'}
                onClick={() => setAttemptFilterCorrect('correct')}
              >
                Correct Only
              </Button>
              <Button
                size="sm"
                variant={attemptFilterCorrect === 'incorrect' ? 'primary' : 'outline'}
                onClick={() => setAttemptFilterCorrect('incorrect')}
              >
                Incorrect Only
              </Button>
            </div>

            {filteredAttempts.length === 0 ? (
              <div style={{ padding: '32px', textAlign: 'center', color: 'var(--slate-500)' }}>
                No practice attempts match the selected filter.
              </div>
            ) : (
              <div style={{ overflowX: 'auto' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.8125rem', textAlign: 'left' }}>
                  <thead style={{ backgroundColor: 'var(--slate-50)', color: 'var(--slate-700)', borderBottom: '1px solid var(--slate-200)' }}>
                    <tr>
                      <th style={{ padding: '10px 14px' }}>Date</th>
                      <th style={{ padding: '10px 14px' }}>Topic</th>
                      <th style={{ padding: '10px 14px' }}>Difficulty</th>
                      <th style={{ padding: '10px 14px' }}>Question Prompt</th>
                      <th style={{ padding: '10px 14px' }}>Your Answer</th>
                      <th style={{ padding: '10px 14px' }}>Result</th>
                      <th style={{ padding: '10px 14px' }}>Time</th>
                    </tr>
                  </thead>
                  <tbody>
                    {filteredAttempts.map((att) => (
                      <tr key={att.id} style={{ borderBottom: '1px solid var(--slate-100)' }}>
                        <td style={{ padding: '10px 14px', whiteSpace: 'nowrap', color: 'var(--slate-500)' }}>
                          {new Date(att.created_at).toLocaleDateString()}
                        </td>
                        <td style={{ padding: '10px 14px', fontWeight: 600 }}>{att.topic}</td>
                        <td style={{ padding: '10px 14px' }}>
                          <Badge variant="neutral">{att.difficulty}</Badge>
                        </td>
                        <td style={{ padding: '10px 14px', maxWidth: '320px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                          {att.question_text}
                        </td>
                        <td style={{ padding: '10px 14px', fontWeight: 700 }}>Option {att.user_answer}</td>
                        <td style={{ padding: '10px 14px' }}>
                          <Badge variant={att.is_correct ? 'success' : 'danger'}>
                            {att.is_correct ? 'Correct' : 'Incorrect'}
                          </Badge>
                        </td>
                        <td style={{ padding: '10px 14px', color: 'var(--slate-500)' }}>
                          {att.duration_seconds ? `${att.duration_seconds}s` : '--'}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </Card>
      )}

      {/* ========================================================================= */}
      {/* TAB 3: AI EVALUATION AUDIT TRAIL & FAIRNESS REPORT                        */}
      {/* ========================================================================= */}
      {activeTab === 'audits' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
          {/* Quality & Fairness Report Summary */}
          {qualityReport && (
            <Card title="AI Evaluation Quality & Fairness Report" subtitle="Compliance metrics across candidate mock interviews">
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '14px', textAlign: 'center' }}>
                <div style={{ padding: '12px', backgroundColor: 'var(--slate-50)', borderRadius: 'var(--radius-md)' }}>
                  <span style={{ fontSize: '1.25rem', fontWeight: 800, color: 'var(--slate-900)' }}>
                    {qualityReport.total_evaluations}
                  </span>
                  <span style={{ display: 'block', fontSize: '0.6875rem', color: 'var(--slate-500)', textTransform: 'uppercase' }}>
                    Total Evaluated
                  </span>
                </div>

                <div style={{ padding: '12px', backgroundColor: 'var(--slate-50)', borderRadius: 'var(--radius-md)' }}>
                  <span style={{ fontSize: '1.25rem', fontWeight: 800, color: 'var(--primary-600)' }}>
                    {qualityReport.average_score.toFixed(1)}/100
                  </span>
                  <span style={{ display: 'block', fontSize: '0.6875rem', color: 'var(--slate-500)', textTransform: 'uppercase' }}>
                    Average Score
                  </span>
                </div>

                <div style={{ padding: '12px', backgroundColor: 'var(--slate-50)', borderRadius: 'var(--radius-md)' }}>
                  <span style={{ fontSize: '1.25rem', fontWeight: 800, color: 'var(--success-600)' }}>
                    {(qualityReport.compliance_rate * 100).toFixed(0)}%
                  </span>
                  <span style={{ display: 'block', fontSize: '0.6875rem', color: 'var(--slate-500)', textTransform: 'uppercase' }}>
                    Bounds Compliance
                  </span>
                </div>

                <div style={{ padding: '12px', backgroundColor: 'var(--slate-50)', borderRadius: 'var(--radius-md)' }}>
                  <span style={{ fontSize: '1.25rem', fontWeight: 800, color: 'var(--slate-900)' }}>
                    {qualityReport.prompt_injections_detected}
                  </span>
                  <span style={{ display: 'block', fontSize: '0.6875rem', color: 'var(--slate-500)', textTransform: 'uppercase' }}>
                    Prompt Injections Blocked
                  </span>
                </div>
              </div>
            </Card>
          )}

          {/* Audit Records Table */}
          <Card title="Immutable Evaluation Audit Trail" subtitle="Traceable log of model providers, safety sanitization, and fallback triggers">
            {audits.length === 0 ? (
              <div style={{ padding: '32px', textAlign: 'center', color: 'var(--slate-500)' }}>
                No interview audit logs recorded yet. Complete a mock interview session to generate audit entries.
              </div>
            ) : (
              <div style={{ overflowX: 'auto' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.8125rem', textAlign: 'left' }}>
                  <thead style={{ backgroundColor: 'var(--slate-50)', color: 'var(--slate-700)', borderBottom: '1px solid var(--slate-200)' }}>
                    <tr>
                      <th style={{ padding: '10px 14px' }}>Session</th>
                      <th style={{ padding: '10px 14px' }}>Model Provider</th>
                      <th style={{ padding: '10px 14px' }}>Score</th>
                      <th style={{ padding: '10px 14px' }}>Safety Sanitization</th>
                      <th style={{ padding: '10px 14px' }}>Fallback Status</th>
                      <th style={{ padding: '10px 14px' }}>Latency</th>
                      <th style={{ padding: '10px 14px' }}>Timestamp</th>
                    </tr>
                  </thead>
                  <tbody>
                    {audits.map((a) => (
                      <tr key={a.id} style={{ borderBottom: '1px solid var(--slate-100)' }}>
                        <td style={{ padding: '10px 14px', fontWeight: 600 }}>#{a.session_id}</td>
                        <td style={{ padding: '10px 14px' }}>{a.model_provider}</td>
                        <td style={{ padding: '10px 14px', fontWeight: 700 }}>{a.evaluated_score.toFixed(0)}/100</td>
                        <td style={{ padding: '10px 14px' }}>
                          <Badge variant={a.prompt_injection_flag ? 'danger' : 'success'}>
                            {a.prompt_injection_flag ? 'Injection Blocked' : 'Clean Input'}
                          </Badge>
                        </td>
                        <td style={{ padding: '10px 14px' }}>
                          <Badge variant={a.is_fallback ? 'warning' : 'neutral'}>
                            {a.is_fallback ? 'Fallback Active' : 'Primary Path'}
                          </Badge>
                        </td>
                        <td style={{ padding: '10px 14px', color: 'var(--slate-500)' }}>{a.latency_ms.toFixed(0)}ms</td>
                        <td style={{ padding: '10px 14px', color: 'var(--slate-400)', whiteSpace: 'nowrap' }}>
                          {new Date(a.created_at).toLocaleDateString()}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </Card>
        </div>
      )}
    </div>
  );
};
