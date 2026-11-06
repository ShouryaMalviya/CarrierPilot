import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Search,
  Sparkles,
  CheckCircle2,
  AlertCircle,
  Briefcase,
  Building,
  Plus,
  RefreshCw,
  FileText,
  Check,
  X,
  BookOpen,
  Cpu,
} from 'lucide-react';
import { useAlert } from '../context/AlertContext';
import { api } from '../services/api';
import {
  Resume,
  ResumeListResponse,
  BatchMatchItem,
  BatchMatchResponse,
  LexicalMatchResponse,
  SemanticStatusResponse,
} from '../types';
import { Card } from '../components/common/Card';
import { Button } from '../components/common/Button';
import { Badge } from '../components/common/Badge';
import { EthicalDisclaimerBanner } from '../components/common/EthicalDisclaimerBanner';

export const MatchingPage: React.FC = () => {
  const { showAlert } = useAlert();
  const navigate = useNavigate();

  // Resumes state
  const [resumes, setResumes] = useState<Resume[]>([]);
  const [selectedResumeId, setSelectedResumeId] = useState<number | null>(null);

  // Engine status
  const [engineStatus, setEngineStatus] = useState<SemanticStatusResponse | null>(null);
  const [useSemantic, setUseSemantic] = useState<boolean>(true);

  // Batch matches and jobs state
  const [batchMatches, setBatchMatches] = useState<BatchMatchItem[]>([]);
  const [isLoadingMatches, setIsLoadingMatches] = useState<boolean>(false);
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [filterType, setFilterType] = useState<'all' | 'benchmark' | 'custom'>('all');

  // Detailed single match inspection modal/drawer
  const [inspectingJobId, setInspectingJobId] = useState<number | null>(null);
  const [detailMatch, setDetailMatch] = useState<LexicalMatchResponse | null>(null);
  const [isLoadingDetail, setIsLoadingDetail] = useState<boolean>(false);

  // New job intake form modal
  const [showAddJobModal, setShowAddJobModal] = useState<boolean>(false);
  const [newTitle, setNewTitle] = useState<string>('');
  const [newCompany, setNewCompany] = useState<string>('');
  const [newSourceUrl, setNewSourceUrl] = useState<string>('');
  const [newDescription, setNewDescription] = useState<string>('');
  const [isSubmittingJob, setIsSubmittingJob] = useState<boolean>(false);
  const [isSeedingDemo, setIsSeedingDemo] = useState<boolean>(false);

  // Initial load: Fetch resumes and engine status
  useEffect(() => {
    const initData = async () => {
      try {
        const [resumesRes, statusRes] = await Promise.all([
          api.get<ResumeListResponse>('/resumes'),
          api.get<SemanticStatusResponse>('/matching/status').catch(() => null),
        ]);

        if (resumesRes?.resumes && resumesRes.resumes.length > 0) {
          setResumes(resumesRes.resumes);
          setSelectedResumeId(resumesRes.resumes[0].id);
        }

        if (statusRes) {
          setEngineStatus(statusRes);
        }
      } catch (err: any) {
        showAlert(err?.message || 'Failed to initialize matching view.', 'danger');
      }
    };

    initData();
  }, []);

  // Compute batch matches whenever selectedResumeId or useSemantic changes
  const fetchBatchMatches = async (resumeId: number) => {
    setIsLoadingMatches(true);
    try {
      const data = await api.post<BatchMatchResponse>(
        `/matching/resumes/${resumeId}/batch?use_semantic=${useSemantic}`
      );
      setBatchMatches(data.matches || []);
    } catch (err: any) {
      showAlert(err?.message || 'Failed to calculate job matches.', 'danger');
      setBatchMatches([]);
    } finally {
      setIsLoadingMatches(false);
    }
  };

  useEffect(() => {
    if (selectedResumeId) {
      fetchBatchMatches(selectedResumeId);
    } else {
      setBatchMatches([]);
    }
  }, [selectedResumeId, useSemantic]);

  // Load detailed explainable breakdown for a specific job
  const handleInspectJob = async (jobId: number) => {
    if (!selectedResumeId) return;
    setInspectingJobId(jobId);
    setIsLoadingDetail(true);
    try {
      const data = await api.post<LexicalMatchResponse>(
        `/matching/resumes/${selectedResumeId}/jobs/${jobId}?use_semantic=${useSemantic}`
      );
      setDetailMatch(data);
    } catch (err: any) {
      showAlert(err?.message || 'Failed to compute match breakdown.', 'danger');
      setDetailMatch(null);
    } finally {
      setIsLoadingDetail(false);
    }
  };

  // Seed standard synthetic demo jobs
  const handleSeedDemoJobs = async () => {
    setIsSeedingDemo(true);
    try {
      await api.post('/jobs/seed-demo');
      showAlert('Benchmark synthetic job postings seeded successfully!', 'success');
      if (selectedResumeId) {
        await fetchBatchMatches(selectedResumeId);
      }
    } catch (err: any) {
      showAlert(err?.message || 'Failed to seed benchmark jobs.', 'danger');
    } finally {
      setIsSeedingDemo(false);
    }
  };

  // Create custom job description
  const handleCreateJob = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newTitle.trim() || !newDescription.trim()) {
      showAlert('Job title and description are required.', 'warning');
      return;
    }

    setIsSubmittingJob(true);
    try {
      const created = await api.post<any>('/jobs', {
        title: newTitle.trim(),
        company: newCompany.trim() || null,
        source_url: newSourceUrl.trim() || null,
        description: newDescription.trim(),
      });

      showAlert(`Job posting "${created.title}" registered with automatic skill extraction!`, 'success');
      setShowAddJobModal(false);
      setNewTitle('');
      setNewCompany('');
      setNewSourceUrl('');
      setNewDescription('');

      if (selectedResumeId) {
        await fetchBatchMatches(selectedResumeId);
        // Automatically inspect the newly created job
        handleInspectJob(created.id);
      }
    } catch (err: any) {
      showAlert(err?.message || 'Failed to intake job description.', 'danger');
    } finally {
      setIsSubmittingJob(false);
    }
  };

  // Filter batch matches
  const filteredMatches = batchMatches.filter((item) => {
    const matchesSearch =
      searchQuery === '' ||
      item.job_title.toLowerCase().includes(searchQuery.toLowerCase()) ||
      (item.company && item.company.toLowerCase().includes(searchQuery.toLowerCase())) ||
      item.missing_required.some((s) => s.toLowerCase().includes(searchQuery.toLowerCase()));

    const matchesType =
      filterType === 'all'
        ? true
        : filterType === 'benchmark'
        ? item.is_synthetic
        : !item.is_synthetic;

    return matchesSearch && matchesType;
  });

  const getScoreColor = (score: number) => {
    if (score >= 75) return 'var(--success-600)';
    if (score >= 50) return 'var(--primary-600)';
    return 'var(--warning-600)';
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
      <EthicalDisclaimerBanner />

      {/* Header & Controls Bar */}
      <div style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', justifyContent: 'space-between', gap: '16px' }}>
        <div>
          <h2 style={{ fontSize: '1.625rem', fontWeight: 800, color: 'var(--slate-900)', margin: 0 }}>
            Job Description Matching & Skill Gap Analysis
          </h2>
          <p style={{ color: 'var(--slate-500)', fontSize: '0.875rem', marginTop: '4px', margin: 0 }}>
            Hybrid explainable ranking combining required skill coverage, semantic similarity, and actionable remediation.
          </p>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <Button
            variant="outline"
            size="sm"
            onClick={handleSeedDemoJobs}
            isLoading={isSeedingDemo}
            icon={<RefreshCw size={14} className={isSeedingDemo ? 'spin' : ''} />}
          >
            Seed Demo Benchmarks
          </Button>

          <Button
            variant="primary"
            size="sm"
            onClick={() => setShowAddJobModal(true)}
            icon={<Plus size={14} />}
          >
            Intake New Job
          </Button>
        </div>
      </div>

      {/* Resume Selector & Engine Mode Card */}
      <Card>
        <div style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', justifyContent: 'space-between', gap: '16px' }}>
          {/* Resume Selection */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px', flex: '1 1 300px' }}>
            <FileText size={20} color="var(--primary-600)" style={{ flexShrink: 0 }} />
            <div style={{ flex: 1 }}>
              <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: 600, color: 'var(--slate-600)', marginBottom: '4px' }}>
                Comparing Against Candidate Resume:
              </label>
              {resumes.length === 0 ? (
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <span style={{ fontSize: '0.875rem', color: 'var(--danger-600)', fontWeight: 500 }}>
                    No resumes uploaded.
                  </span>
                  <Button size="sm" variant="outline" onClick={() => navigate('/resumes')}>
                    Upload Resume
                  </Button>
                </div>
              ) : (
                <select
                  className="input"
                  value={selectedResumeId || ''}
                  onChange={(e) => setSelectedResumeId(Number(e.target.value))}
                  style={{ fontWeight: 600 }}
                >
                  {resumes.map((r) => (
                    <option key={r.id} value={r.id}>
                      {r.original_filename} ({new Date(r.created_at).toLocaleDateString()})
                    </option>
                  ))}
                </select>
              )}
            </div>
          </div>

          {/* Similarity Mode & Semantic Provider Status */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '16px', flexWrap: 'wrap' }}>
            <label
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                cursor: 'pointer',
                userSelect: 'none',
                fontSize: '0.8125rem',
                fontWeight: 600,
                color: 'var(--slate-700)',
              }}
            >
              <input
                type="checkbox"
                checked={useSemantic}
                onChange={(e) => setUseSemantic(e.target.checked)}
                style={{ width: '16px', height: '16px', cursor: 'pointer' }}
              />
              <Cpu size={16} color="var(--primary-600)" />
              Neural Semantic Embeddings
            </label>

            <Badge variant={engineStatus?.is_available ? 'success' : 'neutral'}>
              {engineStatus?.is_available
                ? `Active: ${engineStatus.provider_type}`
                : 'Deterministic Lexical Fallback'}
            </Badge>
          </div>
        </div>
      </Card>

      {/* Main Grid: Match List (Left) + Detail Breakdown (Right) */}
      <div style={{ display: 'grid', gridTemplateColumns: detailMatch ? '1.1fr 1.3fr' : '1fr', gap: '24px', alignItems: 'start' }}>
        {/* Left Column: Job Postings & Match Rankings */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          {/* Search & Filter Bar */}
          <div
            style={{
              display: 'flex',
              flexWrap: 'wrap',
              alignItems: 'center',
              justifyContent: 'space-between',
              gap: '12px',
              padding: '12px 16px',
              backgroundColor: '#ffffff',
              borderRadius: 'var(--radius-lg)',
              border: '1px solid var(--slate-200)',
            }}
          >
            <div style={{ position: 'relative', flex: '1 1 200px' }}>
              <Search
                size={16}
                style={{
                  position: 'absolute',
                  left: '12px',
                  top: '50%',
                  transform: 'translateY(-50%)',
                  color: 'var(--slate-400)',
                }}
              />
              <input
                type="text"
                className="input"
                style={{ paddingLeft: '36px' }}
                placeholder="Search jobs by title, company, or skill..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
              />
            </div>

            <div style={{ display: 'flex', gap: '6px' }}>
              <Button
                size="sm"
                variant={filterType === 'all' ? 'primary' : 'outline'}
                onClick={() => setFilterType('all')}
              >
                All ({batchMatches.length})
              </Button>
              <Button
                size="sm"
                variant={filterType === 'benchmark' ? 'primary' : 'outline'}
                onClick={() => setFilterType('benchmark')}
              >
                Benchmarks
              </Button>
              <Button
                size="sm"
                variant={filterType === 'custom' ? 'primary' : 'outline'}
                onClick={() => setFilterType('custom')}
              >
                Custom Jobs
              </Button>
            </div>
          </div>

          {/* Match Rankings List */}
          {isLoadingMatches ? (
            <div style={{ padding: '60px', textAlign: 'center', color: 'var(--slate-500)', backgroundColor: '#ffffff', borderRadius: 'var(--radius-lg)' }}>
              <div
                style={{
                  width: '32px',
                  height: '32px',
                  border: '3px solid var(--slate-200)',
                  borderTopColor: 'var(--primary-600)',
                  borderRadius: '50%',
                  margin: '0 auto 12px',
                  animation: 'spin 0.8s linear infinite',
                }}
              />
              <p style={{ margin: 0, fontWeight: 500 }}>Evaluating candidate resume against job opportunities...</p>
            </div>
          ) : filteredMatches.length === 0 ? (
            <Card>
              <div style={{ padding: '40px 20px', textAlign: 'center', color: 'var(--slate-500)' }}>
                <Briefcase size={36} color="var(--slate-300)" style={{ margin: '0 auto 12px' }} />
                <h4 style={{ margin: '0 0 6px', color: 'var(--slate-800)' }}>No Job Matches Found</h4>
                <p style={{ margin: '0 0 16px', fontSize: '0.8125rem' }}>
                  {batchMatches.length === 0
                    ? 'No jobs registered yet. Seed the standard benchmark dataset or intake a custom job description.'
                    : 'No jobs match your search filters.'}
                </p>
                {batchMatches.length === 0 && (
                  <Button variant="primary" size="sm" onClick={handleSeedDemoJobs} isLoading={isSeedingDemo}>
                    Seed 5 Benchmark Demo Jobs
                  </Button>
                )}
              </div>
            </Card>
          ) : (
            filteredMatches.map((match) => {
              const isSelected = inspectingJobId === match.job_id;
              const overallPercent = match.overall_score.toFixed(0);

              return (
                <div
                  key={match.job_id}
                  onClick={() => handleInspectJob(match.job_id)}
                  style={{
                    padding: '18px 20px',
                    borderRadius: 'var(--radius-lg)',
                    border: isSelected ? '2px solid var(--primary-600)' : '1px solid var(--slate-200)',
                    backgroundColor: isSelected ? 'var(--primary-50)' : '#ffffff',
                    cursor: 'pointer',
                    boxShadow: isSelected ? 'var(--shadow-md)' : 'var(--shadow-sm)',
                    transition: 'all 0.15s ease',
                    display: 'flex',
                    flexDirection: 'column',
                    gap: '12px',
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: '12px' }}>
                    <div>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
                        <h3 style={{ fontSize: '1.0625rem', fontWeight: 700, margin: 0, color: 'var(--slate-900)' }}>
                          {match.job_title}
                        </h3>
                        {match.is_synthetic && <Badge variant="neutral">Benchmark Demo</Badge>}
                      </div>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.8125rem', color: 'var(--slate-500)' }}>
                        <Building size={14} />
                        <span>{match.company || 'Open Organization'}</span>
                      </div>
                    </div>

                    {/* Match Score Badge */}
                    <div style={{ textAlign: 'right', flexShrink: 0 }}>
                      <div style={{ fontSize: '1.5rem', fontWeight: 800, color: getScoreColor(match.overall_score) }}>
                        {overallPercent}%
                      </div>
                      <span style={{ fontSize: '0.6875rem', textTransform: 'uppercase', fontWeight: 700, color: 'var(--slate-400)' }}>
                        Alignment Score
                      </span>
                    </div>
                  </div>

                  {/* Factor Breakdown Bars */}
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px', fontSize: '0.75rem' }}>
                    <div>
                      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '2px', color: 'var(--slate-600)' }}>
                        <span>Required Skills</span>
                        <strong>{(match.required_coverage * 100).toFixed(0)}%</strong>
                      </div>
                      <div style={{ height: '5px', backgroundColor: 'var(--slate-200)', borderRadius: '3px', overflow: 'hidden' }}>
                        <div
                          style={{
                            height: '100%',
                            width: `${match.required_coverage * 100}%`,
                            backgroundColor: 'var(--success-600)',
                            borderRadius: '3px',
                          }}
                        />
                      </div>
                    </div>

                    <div>
                      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '2px', color: 'var(--slate-600)' }}>
                        <span>Content Similarity</span>
                        <strong>
                          {match.semantic_similarity !== null
                            ? (match.semantic_similarity * 100).toFixed(0)
                            : (match.tfidf_similarity * 100).toFixed(0)}
                          %
                        </strong>
                      </div>
                      <div style={{ height: '5px', backgroundColor: 'var(--slate-200)', borderRadius: '3px', overflow: 'hidden' }}>
                        <div
                          style={{
                            height: '100%',
                            width: `${
                              match.semantic_similarity !== null
                                ? match.semantic_similarity * 100
                                : match.tfidf_similarity * 100
                            }%`,
                            backgroundColor: 'var(--primary-600)',
                            borderRadius: '3px',
                          }}
                        />
                      </div>
                    </div>
                  </div>

                  {/* Missing Skills Warning */}
                  {match.missing_required.length > 0 ? (
                    <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.75rem', color: 'var(--danger-700)' }}>
                      <AlertCircle size={14} color="var(--danger-600)" />
                      <span>Missing {match.missing_required_count} required: </span>
                      <strong style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                        {match.missing_required.slice(0, 3).join(', ')}
                        {match.missing_required.length > 3 ? '...' : ''}
                      </strong>
                    </div>
                  ) : (
                    <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.75rem', color: 'var(--success-700)' }}>
                      <CheckCircle2 size={14} color="var(--success-600)" />
                      <span>All required qualifications covered by resume!</span>
                    </div>
                  )}
                </div>
              );
            })
          )}
        </div>

        {/* Right Column: Detailed Match & Skill Gap Breakdown */}
        {detailMatch && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
            <Card
              title={`Match Diagnostics: ${detailMatch.job_title}`}
              subtitle={detailMatch.company || 'Open Organization'}
            >
              {isLoadingDetail ? (
                <div style={{ padding: '40px', textAlign: 'center', color: 'var(--slate-500)' }}>
                  Loading explainable breakdown...
                </div>
              ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
                  {/* Synthesis Explanation Card */}
                  <div
                    style={{
                      padding: '14px 16px',
                      backgroundColor: 'var(--primary-50)',
                      border: '1px solid var(--primary-200)',
                      borderRadius: 'var(--radius-md)',
                      fontSize: '0.8125rem',
                      color: 'var(--primary-900)',
                      lineHeight: 1.5,
                    }}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontWeight: 700, marginBottom: '4px' }}>
                      <Sparkles size={16} color="var(--primary-600)" />
                      Explainable Synthesis
                    </div>
                    {detailMatch.explanation_summary}
                  </div>

                  {/* Component Score Decomposition */}
                  <div>
                    <h4 style={{ fontSize: '0.875rem', fontWeight: 700, color: 'var(--slate-800)', marginBottom: '10px' }}>
                      Score Decomposition
                    </h4>
                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '10px', textAlign: 'center' }}>
                      <div style={{ padding: '10px', backgroundColor: 'var(--slate-50)', borderRadius: 'var(--radius-md)' }}>
                        <div style={{ fontSize: '1.25rem', fontWeight: 800, color: 'var(--slate-900)' }}>
                          {(detailMatch.scores.required_coverage * 100).toFixed(0)}%
                        </div>
                        <span style={{ fontSize: '0.6875rem', color: 'var(--slate-500)', textTransform: 'uppercase' }}>
                          Required (50%)
                        </span>
                      </div>

                      <div style={{ padding: '10px', backgroundColor: 'var(--slate-50)', borderRadius: 'var(--radius-md)' }}>
                        <div style={{ fontSize: '1.25rem', fontWeight: 800, color: 'var(--slate-900)' }}>
                          {(detailMatch.scores.preferred_coverage * 100).toFixed(0)}%
                        </div>
                        <span style={{ fontSize: '0.6875rem', color: 'var(--slate-500)', textTransform: 'uppercase' }}>
                          Preferred (20%)
                        </span>
                      </div>

                      <div style={{ padding: '10px', backgroundColor: 'var(--slate-50)', borderRadius: 'var(--radius-md)' }}>
                        <div style={{ fontSize: '1.25rem', fontWeight: 800, color: 'var(--slate-900)' }}>
                          {detailMatch.scores.semantic_similarity !== null
                            ? (detailMatch.scores.semantic_similarity * 100).toFixed(0)
                            : (detailMatch.scores.tfidf_similarity * 100).toFixed(0)}
                          %
                        </div>
                        <span style={{ fontSize: '0.6875rem', color: 'var(--slate-500)', textTransform: 'uppercase' }}>
                          Similarity (30%)
                        </span>
                      </div>
                    </div>
                  </div>

                  {/* Skill Gap Breakdown: Matched vs Missing */}
                  <div>
                    <h4 style={{ fontSize: '0.875rem', fontWeight: 700, color: 'var(--slate-800)', marginBottom: '8px' }}>
                      Skill Gap Matrix
                    </h4>

                    {/* Matched Required */}
                    <div style={{ marginBottom: '12px' }}>
                      <span style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--success-700)', display: 'block', marginBottom: '4px' }}>
                        Matched Required Qualifications ({detailMatch.skill_gap.matched_required.length})
                      </span>
                      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
                        {detailMatch.skill_gap.matched_required.length === 0 ? (
                          <span style={{ fontSize: '0.75rem', color: 'var(--slate-400)' }}>None detected</span>
                        ) : (
                          detailMatch.skill_gap.matched_required.map((s) => (
                            <Badge key={s} variant="success">
                              <Check size={12} /> {s}
                            </Badge>
                          ))
                        )}
                      </div>
                    </div>

                    {/* Missing Required */}
                    <div style={{ marginBottom: '12px' }}>
                      <span style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--danger-700)', display: 'block', marginBottom: '4px' }}>
                        Missing Required Qualifications ({detailMatch.skill_gap.missing_required.length})
                      </span>
                      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
                        {detailMatch.skill_gap.missing_required.length === 0 ? (
                          <span style={{ fontSize: '0.75rem', color: 'var(--success-600)' }}>All required skills present!</span>
                        ) : (
                          detailMatch.skill_gap.missing_required.map((s) => (
                            <Badge key={s} variant="danger">
                              <X size={12} /> {s}
                            </Badge>
                          ))
                        )}
                      </div>
                    </div>

                    {/* Preferred Skills */}
                    <div>
                      <span style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--slate-600)', display: 'block', marginBottom: '4px' }}>
                        Preferred Qualifications (Bonus)
                      </span>
                      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
                        {detailMatch.skill_gap.matched_preferred.map((s) => (
                          <Badge key={s} variant="primary">
                            <Check size={12} /> {s}
                          </Badge>
                        ))}
                        {detailMatch.skill_gap.missing_preferred.map((s) => (
                          <Badge key={s} variant="neutral">
                            {s}
                          </Badge>
                        ))}
                      </div>
                    </div>
                  </div>

                  {/* Verbatim Evidence Citations */}
                  {detailMatch.evidence.length > 0 && (
                    <div>
                      <h4 style={{ fontSize: '0.875rem', fontWeight: 700, color: 'var(--slate-800)', marginBottom: '8px' }}>
                        Verbatim Resume Evidence Citations
                      </h4>
                      <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', maxHeight: '180px', overflowY: 'auto' }}>
                        {detailMatch.evidence.map((ev, idx) => (
                          <div
                            key={idx}
                            style={{
                              padding: '8px 12px',
                              backgroundColor: 'var(--slate-50)',
                              borderRadius: 'var(--radius-sm)',
                              border: '1px solid var(--slate-200)',
                              fontSize: '0.75rem',
                            }}
                          >
                            <div style={{ display: 'flex', justifyContent: 'space-between', fontWeight: 600, color: 'var(--slate-800)', marginBottom: '2px' }}>
                              <span>{ev.canonical_name}</span>
                              <span style={{ color: 'var(--primary-600)' }}>{((ev.confidence_score ?? 1.0) * 100).toFixed(0)}% confidence</span>
                            </div>
                            <p style={{ margin: 0, color: 'var(--slate-600)', fontStyle: 'italic', lineHeight: 1.4 }}>
                              "{ev.evidence_snippet || 'Verified qualification citation'}"
                            </p>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Actionable Learning Recommendations */}
                  {detailMatch.recommendations.length > 0 && (
                    <div>
                      <h4 style={{ fontSize: '0.875rem', fontWeight: 700, color: 'var(--slate-800)', marginBottom: '8px' }}>
                        Skill Remediation Recommendations
                      </h4>
                      <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                        {detailMatch.recommendations.map((rec, idx) => (
                          <div
                            key={idx}
                            style={{
                              padding: '12px 14px',
                              backgroundColor: 'var(--warning-50)',
                              border: '1px solid var(--warning-200)',
                              borderRadius: 'var(--radius-md)',
                            }}
                          >
                            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '4px' }}>
                              <span style={{ fontWeight: 700, fontSize: '0.8125rem', color: 'var(--warning-900)' }}>
                                {rec.skill_name}
                              </span>
                              <Badge variant={rec.priority === 'high' ? 'danger' : 'warning'}>
                                {rec.priority} priority
                              </Badge>
                            </div>
                            <p style={{ margin: '0 0 6px', fontSize: '0.75rem', color: 'var(--warning-800)', lineHeight: 1.4 }}>
                              {rec.rationale}
                            </p>
                            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                              <span style={{ fontSize: '0.75rem', color: 'var(--slate-600)', fontWeight: 500 }}>
                                Action: {rec.suggested_action}
                              </span>
                              <Button
                                size="sm"
                                variant="outline"
                                onClick={() => navigate('/practice')}
                                icon={<BookOpen size={12} />}
                              >
                                Practice Topics
                              </Button>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Ethical Footnote */}
                  <div
                    style={{
                      padding: '10px 12px',
                      backgroundColor: 'var(--slate-50)',
                      borderRadius: 'var(--radius-sm)',
                      fontSize: '0.6875rem',
                      color: 'var(--slate-500)',
                      lineHeight: 1.4,
                    }}
                  >
                    <strong>Ethical Boundary:</strong> {detailMatch.disclaimer}
                  </div>
                </div>
              )}
            </Card>
          </div>
        )}
      </div>

      {/* Intake Job Description Modal */}
      {showAddJobModal && (
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
              maxWidth: '620px',
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
                <Briefcase size={20} color="var(--primary-600)" />
                <h3 style={{ fontSize: '1.25rem', fontWeight: 800, margin: 0, color: 'var(--slate-900)' }}>
                  Intake External Job Description
                </h3>
              </div>
              <button
                type="button"
                onClick={() => setShowAddJobModal(false)}
                style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--slate-400)' }}
              >
                <X size={20} />
              </button>
            </div>

            <p style={{ fontSize: '0.8125rem', color: 'var(--slate-500)', margin: '0 0 20px', lineHeight: 1.5 }}>
              Paste any job posting text. The system automatically segments required and preferred skills using our canonical taxonomy.
            </p>

            <form onSubmit={handleCreateJob} style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
              <div>
                <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: 600, color: 'var(--slate-700)', marginBottom: '4px' }}>
                  Job Designation / Title *
                </label>
                <input
                  type="text"
                  required
                  className="input"
                  placeholder="e.g. Senior Backend Engineer (Python / FastAPI)"
                  value={newTitle}
                  onChange={(e) => setNewTitle(e.target.value)}
                />
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                <div>
                  <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: 600, color: 'var(--slate-700)', marginBottom: '4px' }}>
                    Company / Organization
                  </label>
                  <input
                    type="text"
                    className="input"
                    placeholder="e.g. Stripe, Acme Corp"
                    value={newCompany}
                    onChange={(e) => setNewCompany(e.target.value)}
                  />
                </div>

                <div>
                  <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: 600, color: 'var(--slate-700)', marginBottom: '4px' }}>
                    Source URL (Optional)
                  </label>
                  <input
                    type="url"
                    className="input"
                    placeholder="https://company.com/careers/job123"
                    value={newSourceUrl}
                    onChange={(e) => setNewSourceUrl(e.target.value)}
                  />
                </div>
              </div>

              <div>
                <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: 600, color: 'var(--slate-700)', marginBottom: '4px' }}>
                  Complete Job Description Text *
                </label>
                <textarea
                  required
                  rows={8}
                  className="textarea"
                  style={{ fontFamily: 'var(--font-sans)', fontSize: '0.8125rem', lineHeight: 1.5 }}
                  placeholder="Paste the full job requirements, responsibilities, and qualifications..."
                  value={newDescription}
                  onChange={(e) => setNewDescription(e.target.value)}
                />
              </div>

              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'flex-end', gap: '10px', marginTop: '10px' }}>
                <Button type="button" variant="outline" onClick={() => setShowAddJobModal(false)}>
                  Cancel
                </Button>
                <Button type="submit" variant="primary" isLoading={isSubmittingJob} icon={<Plus size={16} />}>
                  Register & Parse Skills
                </Button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
