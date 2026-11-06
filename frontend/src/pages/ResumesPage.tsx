import React, { useState, useEffect, useRef } from 'react';
import {
  FileUp,
  FileText,
  Trash2,
  RefreshCw,
  AlertCircle,
  Plus,
  Sparkles,
  Check,
  X,
  Info,
  Edit2,
  Save,
} from 'lucide-react';
import { useAlert } from '../context/AlertContext';
import { api } from '../services/api';
import { Resume, ResumeSkill, ResumeSectionsResponse, ResumeListResponse } from '../types';
import { Card } from '../components/common/Card';
import { Button } from '../components/common/Button';
import { Badge } from '../components/common/Badge';
import { EthicalDisclaimerBanner } from '../components/common/EthicalDisclaimerBanner';

const MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024; // 10MB
const ALLOWED_EXTENSIONS = ['.pdf', '.docx'];

export const ResumesPage: React.FC = () => {
  const { showAlert } = useAlert();
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [resumes, setResumes] = useState<Resume[]>([]);
  const [selectedResumeId, setSelectedResumeId] = useState<number | null>(null);
  const [sectionsData, setSectionsData] = useState<ResumeSectionsResponse | null>(null);

  const [isLoadingList, setIsLoadingList] = useState<boolean>(true);
  const [isLoadingDetails, setIsLoadingDetails] = useState<boolean>(false);
  const [isUploading, setIsUploading] = useState<boolean>(false);
  const [isReparsing, setIsReparsing] = useState<boolean>(false);
  const [isDragging, setIsDragging] = useState<boolean>(false);

  // Skill editing state
  const [newSkillName, setNewSkillName] = useState<string>('');
  const [newSkillSnippet, setNewSkillSnippet] = useState<string>('');
  const [isAddingSkill, setIsAddingSkill] = useState<boolean>(false);
  const [inspectingSkill, setInspectingSkill] = useState<ResumeSkill | null>(null);

  // Section editing state
  const [editingSectionKey, setEditingSectionKey] = useState<string | null>(null);
  const [editingSectionText, setEditingSectionText] = useState<string>('');
  const [isSavingSection, setIsSavingSection] = useState<boolean>(false);

  // Active section tab
  const [activeTab, setActiveTab] = useState<'skills' | 'sections'>('skills');

  // Load user resumes on mount
  const fetchResumes = async (selectIdAfterLoad?: number) => {
    setIsLoadingList(true);
    try {
      const res = await api.get<ResumeListResponse>('/resumes');
      setResumes(res.resumes || []);

      if (res.resumes && res.resumes.length > 0) {
        if (selectIdAfterLoad && res.resumes.some((r) => r.id === selectIdAfterLoad)) {
          setSelectedResumeId(selectIdAfterLoad);
        } else if (!selectedResumeId || !res.resumes.some((r) => r.id === selectedResumeId)) {
          setSelectedResumeId(res.resumes[0].id);
        }
      } else {
        setSelectedResumeId(null);
        setSectionsData(null);
      }
    } catch (err: any) {
      showAlert(err?.message || 'Failed to fetch resume list.', 'danger');
    } finally {
      setIsLoadingList(false);
    }
  };

  useEffect(() => {
    fetchResumes();
  }, []);

  // Load sections and skills when selected resume changes
  const fetchResumeDetails = async (resumeId: number) => {
    setIsLoadingDetails(true);
    try {
      const data = await api.get<ResumeSectionsResponse>(`/resumes/${resumeId}/sections`);
      setSectionsData(data);
    } catch (err: any) {
      showAlert(err?.message || 'Failed to load resume sections and skills.', 'danger');
      setSectionsData(null);
    } finally {
      setIsLoadingDetails(false);
    }
  };

  useEffect(() => {
    if (selectedResumeId) {
      fetchResumeDetails(selectedResumeId);
      setEditingSectionKey(null);
      setInspectingSkill(null);
    } else {
      setSectionsData(null);
    }
  }, [selectedResumeId]);

  // Handle secure file upload
  const handleFileUpload = async (file: File) => {
    const ext = '.' + file.name.split('.').pop()?.toLowerCase();
    if (!ALLOWED_EXTENSIONS.includes(ext)) {
      showAlert('Invalid file type. Please upload a standard PDF or DOCX resume document.', 'danger');
      return;
    }

    if (file.size > MAX_FILE_SIZE_BYTES) {
      showAlert('File size exceeds the 10MB limit. Please upload a smaller document.', 'danger');
      return;
    }

    setIsUploading(true);
    const formData = new FormData();
    formData.append('file', file);

    try {
      const uploaded = await api.post<Resume>('/resumes/upload', formData);
      showAlert(`Resume "${file.name}" uploaded and parsed successfully!`, 'success');
      await fetchResumes(uploaded.id);
    } catch (err: any) {
      const msg = err?.data?.error?.message || err?.message || 'Failed to upload resume.';
      showAlert(msg, 'danger');
    } finally {
      setIsUploading(false);
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    }
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      handleFileUpload(e.dataTransfer.files[0]);
    }
  };

  // Re-trigger extraction
  const handleReparse = async () => {
    if (!selectedResumeId) return;
    setIsReparsing(true);
    try {
      await api.post(`/resumes/${selectedResumeId}/extract`);
      showAlert('Resume text extraction and skill parsing re-executed successfully.', 'success');
      await fetchResumeDetails(selectedResumeId);
      await fetchResumes(selectedResumeId);
    } catch (err: any) {
      showAlert(err?.message || 'Failed to re-parse resume.', 'danger');
    } finally {
      setIsReparsing(false);
    }
  };

  // Delete resume
  const handleDeleteResume = async (id: number) => {
    if (!window.confirm('Are you sure you want to delete this resume? This will also remove extracted skills.')) {
      return;
    }

    try {
      await api.delete(`/resumes/${id}`);
      showAlert('Resume deleted successfully.', 'success');
      await fetchResumes();
    } catch (err: any) {
      showAlert(err?.message || 'Failed to delete resume.', 'danger');
    }
  };

  // Toggle user confirmation of skill
  const handleToggleConfirmSkill = async (skill: ResumeSkill) => {
    if (!selectedResumeId) return;
    try {
      const updated = await api.put<ResumeSkill>(
        `/resumes/${selectedResumeId}/skills/${skill.id}`,
        { is_user_confirmed: !skill.is_user_confirmed }
      );
      if (sectionsData) {
        setSectionsData({
          ...sectionsData,
          skills: sectionsData.skills.map((s) => (s.id === skill.id ? { ...s, is_user_confirmed: updated.is_user_confirmed } : s)),
        });
      }
      showAlert(`Skill "${skill.canonical_name}" marked as ${!skill.is_user_confirmed ? 'confirmed' : 'unconfirmed'}.`, 'success');
    } catch (err: any) {
      showAlert(err?.message || 'Failed to update skill confirmation.', 'danger');
    }
  };

  // Delete skill
  const handleDeleteSkill = async (skillId: number, skillName: string) => {
    if (!selectedResumeId) return;
    try {
      await api.delete(`/resumes/${selectedResumeId}/skills/${skillId}`);
      if (sectionsData) {
        setSectionsData({
          ...sectionsData,
          skills: sectionsData.skills.filter((s) => s.id !== skillId),
        });
      }
      if (inspectingSkill?.id === skillId) {
        setInspectingSkill(null);
      }
      showAlert(`Skill "${skillName}" removed from resume profile.`, 'success');
    } catch (err: any) {
      showAlert(err?.message || 'Failed to remove skill.', 'danger');
    }
  };

  // Add missing skill
  const handleAddSkill = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedResumeId || !newSkillName.trim()) return;

    setIsAddingSkill(true);
    try {
      const created = await api.post<ResumeSkill>(`/resumes/${selectedResumeId}/skills`, {
        skill_name: newSkillName.trim(),
        evidence_snippet: newSkillSnippet.trim() || 'Verified candidate competency',
      });

      if (sectionsData) {
        setSectionsData({
          ...sectionsData,
          skills: [...sectionsData.skills, created],
        });
      }
      setNewSkillName('');
      setNewSkillSnippet('');
      showAlert(`Skill "${created.canonical_name}" added and verified!`, 'success');
    } catch (err: any) {
      showAlert(err?.message || 'Failed to add custom skill.', 'danger');
    } finally {
      setIsAddingSkill(false);
    }
  };

  // Edit section text
  const handleStartEditSection = (key: string, text: string) => {
    setEditingSectionKey(key);
    setEditingSectionText(text);
  };

  const handleSaveSection = async (key: string) => {
    if (!selectedResumeId || !sectionsData) return;
    setIsSavingSection(true);
    try {
      const updatedSections = {
        ...sectionsData.sections,
        [key]: editingSectionText,
      };
      const res = await api.put<ResumeSectionsResponse>(`/resumes/${selectedResumeId}/sections`, {
        sections: updatedSections,
      });
      setSectionsData(res);
      setEditingSectionKey(null);
      showAlert(`Section "${key}" updated successfully.`, 'success');
    } catch (err: any) {
      showAlert(err?.message || 'Failed to update section text.', 'danger');
    } finally {
      setIsSavingSection(false);
    }
  };

  const formatFileSize = (bytes: number): string => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  const selectedResume = resumes.find((r) => r.id === selectedResumeId);

  // Group skills by category
  const skillsByCategory: Record<string, ResumeSkill[]> = {};
  if (sectionsData?.skills) {
    for (const skill of sectionsData.skills) {
      const cat = skill.category || 'other';
      if (!skillsByCategory[cat]) skillsByCategory[cat] = [];
      skillsByCategory[cat].push(skill);
    }
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
      <EthicalDisclaimerBanner />

      {/* Header */}
      <div style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', justifyContent: 'space-between', gap: '16px' }}>
        <div>
          <h2 style={{ fontSize: '1.625rem', fontWeight: 800, color: 'var(--slate-900)', margin: 0 }}>
            Resume Workspace & Skill Taxonomy
          </h2>
          <p style={{ color: 'var(--slate-500)', fontSize: '0.875rem', marginTop: '4px', margin: 0 }}>
            Upload PDF/DOCX resumes, inspect segmented sections, verify parsed skills, and review snippet evidence.
          </p>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <input
            type="file"
            ref={fileInputRef}
            onChange={(e) => e.target.files && e.target.files[0] && handleFileUpload(e.target.files[0])}
            accept=".pdf,.docx,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            style={{ display: 'none' }}
          />
          <Button
            variant="primary"
            onClick={() => fileInputRef.current?.click()}
            isLoading={isUploading}
            icon={<FileUp size={16} />}
          >
            Upload New Resume
          </Button>
        </div>
      </div>

      {/* Main Workspace Layout */}
      <div style={{ display: 'grid', gridTemplateColumns: 'minmax(280px, 340px) 1fr', gap: '24px', alignItems: 'start' }}>
        {/* Left Column: Upload Dropzone & Resume List */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
          {/* Drag & Drop Card */}
          <div
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
            onClick={() => fileInputRef.current?.click()}
            style={{
              padding: '28px 20px',
              border: isDragging ? '2px dashed var(--primary-600)' : '2px dashed var(--slate-300)',
              borderRadius: 'var(--radius-lg)',
              backgroundColor: isDragging ? 'var(--primary-50)' : '#ffffff',
              textAlign: 'center',
              cursor: 'pointer',
              transition: 'all 0.2s ease',
            }}
          >
            <div
              style={{
                width: '44px',
                height: '44px',
                borderRadius: '12px',
                backgroundColor: 'var(--primary-100)',
                color: 'var(--primary-700)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                margin: '0 auto 12px',
              }}
            >
              <FileUp size={22} />
            </div>
            <p style={{ fontWeight: 600, color: 'var(--slate-800)', fontSize: '0.875rem', margin: '0 0 4px' }}>
              Drag & drop resume here, or <span style={{ color: 'var(--primary-600)' }}>browse</span>
            </p>
            <p style={{ fontSize: '0.75rem', color: 'var(--slate-500)', margin: 0 }}>
              Supports PDF and DOCX files up to 10MB
            </p>
          </div>

          {/* Uploaded Resumes Selector */}
          <Card title="Uploaded Resumes" subtitle={`${resumes.length} document${resumes.length === 1 ? '' : 's'} on file`}>
            {isLoadingList ? (
              <div style={{ padding: '24px', textAlign: 'center', color: 'var(--slate-500)', fontSize: '0.875rem' }}>
                Loading candidate resumes...
              </div>
            ) : resumes.length === 0 ? (
              <div style={{ padding: '24px', textAlign: 'center', color: 'var(--slate-500)', fontSize: '0.875rem' }}>
                No resumes uploaded yet. Upload a resume to begin skill taxonomy extraction.
              </div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                {resumes.map((resume) => {
                  const isSelected = resume.id === selectedResumeId;
                  return (
                    <div
                      key={resume.id}
                      onClick={() => setSelectedResumeId(resume.id)}
                      style={{
                        padding: '12px 14px',
                        borderRadius: 'var(--radius-md)',
                        border: isSelected ? '2px solid var(--primary-600)' : '1px solid var(--slate-200)',
                        backgroundColor: isSelected ? 'var(--primary-50)' : '#ffffff',
                        cursor: 'pointer',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'space-between',
                        gap: '10px',
                        transition: 'all 0.15s ease',
                      }}
                    >
                      <div style={{ display: 'flex', alignItems: 'center', gap: '10px', overflow: 'hidden' }}>
                        <FileText size={18} color={isSelected ? 'var(--primary-600)' : 'var(--slate-400)'} style={{ flexShrink: 0 }} />
                        <div style={{ overflow: 'hidden' }}>
                          <span
                            style={{
                              display: 'block',
                              fontSize: '0.8125rem',
                              fontWeight: 600,
                              color: isSelected ? 'var(--primary-900)' : 'var(--slate-800)',
                              whiteSpace: 'nowrap',
                              overflow: 'hidden',
                              textOverflow: 'ellipsis',
                            }}
                          >
                            {resume.original_filename}
                          </span>
                          <span style={{ fontSize: '0.6875rem', color: 'var(--slate-400)' }}>
                            {formatFileSize(resume.file_size_bytes)} • {new Date(resume.created_at).toLocaleDateString()}
                          </span>
                        </div>
                      </div>

                      <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                        <Badge
                          variant={
                            resume.parse_status === 'success'
                              ? 'success'
                              : resume.parse_status === 'warning'
                              ? 'warning'
                              : 'neutral'
                          }
                          style={{ fontSize: '0.6875rem' }}
                        >
                          {resume.parse_status}
                        </Badge>

                        <button
                          type="button"
                          onClick={(e) => {
                            e.stopPropagation();
                            handleDeleteResume(resume.id);
                          }}
                          style={{
                            background: 'none',
                            border: 'none',
                            color: 'var(--slate-400)',
                            cursor: 'pointer',
                            padding: '4px',
                            display: 'flex',
                            alignItems: 'center',
                          }}
                          title="Delete resume"
                        >
                          <Trash2 size={14} />
                        </button>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </Card>
        </div>

        {/* Right Column: Selected Resume Details, Skills & Section View */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
          {selectedResume ? (
            <>
              {/* Document Overview Bar */}
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
                  gap: '12px',
                }}
              >
                <div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <h3 style={{ fontSize: '1.125rem', fontWeight: 700, margin: 0, color: 'var(--slate-900)' }}>
                      {selectedResume.original_filename}
                    </h3>
                    <Badge variant="primary">{formatFileSize(selectedResume.file_size_bytes)}</Badge>
                  </div>
                  <span style={{ fontSize: '0.75rem', color: 'var(--slate-500)', marginTop: '2px', display: 'block' }}>
                    Parsed with engine v{selectedResume.parser_version || '1.0.0'} • Detected {sectionsData?.skills.length || 0} skills
                  </span>
                </div>

                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={handleReparse}
                    isLoading={isReparsing}
                    icon={<RefreshCw size={14} className={isReparsing ? 'spin' : ''} />}
                  >
                    Re-extract Skills
                  </Button>
                </div>
              </div>

              {/* Navigation Tabs (Skills Taxonomy vs Segmented Sections) */}
              <div style={{ display: 'flex', borderBottom: '1px solid var(--slate-200)', gap: '8px' }}>
                <button
                  type="button"
                  onClick={() => setActiveTab('skills')}
                  style={{
                    padding: '10px 16px',
                    fontSize: '0.875rem',
                    fontWeight: 600,
                    border: 'none',
                    borderBottom: activeTab === 'skills' ? '2px solid var(--primary-600)' : '2px solid transparent',
                    backgroundColor: 'transparent',
                    color: activeTab === 'skills' ? 'var(--primary-600)' : 'var(--slate-600)',
                    cursor: 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '6px',
                  }}
                >
                  <Sparkles size={16} />
                  Extracted Skills Taxonomy ({sectionsData?.skills.length || 0})
                </button>

                <button
                  type="button"
                  onClick={() => setActiveTab('sections')}
                  style={{
                    padding: '10px 16px',
                    fontSize: '0.875rem',
                    fontWeight: 600,
                    border: 'none',
                    borderBottom: activeTab === 'sections' ? '2px solid var(--primary-600)' : '2px solid transparent',
                    backgroundColor: 'transparent',
                    color: activeTab === 'sections' ? 'var(--primary-600)' : 'var(--slate-600)',
                    cursor: 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '6px',
                  }}
                >
                  <FileText size={16} />
                  Segmented Sections ({Object.keys(sectionsData?.sections || {}).length})
                </button>
              </div>

              {/* Tab 1: Extracted Skills Taxonomy */}
              {activeTab === 'skills' && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
                  {/* Add Skill Bar */}
                  <Card title="Add / Verify Missing Skill" subtitle="Manually register a verified competency with optional evidence snippet">
                    <form onSubmit={handleAddSkill} style={{ display: 'flex', flexWrap: 'wrap', gap: '10px', alignItems: 'flex-end' }}>
                      <div style={{ flex: '1 1 200px' }}>
                        <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: 600, color: 'var(--slate-600)', marginBottom: '4px' }}>
                          Skill Name
                        </label>
                        <input
                          type="text"
                          className="input"
                          placeholder="e.g. FastAPI, Docker, PyTorch"
                          value={newSkillName}
                          onChange={(e) => setNewSkillName(e.target.value)}
                          required
                        />
                      </div>

                      <div style={{ flex: '2 1 300px' }}>
                        <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: 600, color: 'var(--slate-600)', marginBottom: '4px' }}>
                          Evidence Note / Project Context (Optional)
                        </label>
                        <input
                          type="text"
                          className="input"
                          placeholder="e.g. Built microservices with async endpoints"
                          value={newSkillSnippet}
                          onChange={(e) => setNewSkillSnippet(e.target.value)}
                        />
                      </div>

                      <Button type="submit" variant="primary" size="sm" isLoading={isAddingSkill} icon={<Plus size={14} />}>
                        Add Skill
                      </Button>
                    </form>
                  </Card>

                  {/* Skills Grouped by Category */}
                  {isLoadingDetails ? (
                    <div style={{ padding: '40px', textAlign: 'center', color: 'var(--slate-500)' }}>
                      Loading parsed skills taxonomy...
                    </div>
                  ) : Object.keys(skillsByCategory).length === 0 ? (
                    <Card>
                      <div style={{ padding: '32px', textAlign: 'center', color: 'var(--slate-500)' }}>
                        <AlertCircle size={28} color="var(--slate-400)" style={{ margin: '0 auto 8px' }} />
                        <p style={{ margin: 0, fontWeight: 500 }}>No skills detected automatically in this document.</p>
                        <p style={{ margin: '4px 0 0', fontSize: '0.8125rem' }}>
                          Add your technical skills using the form above or check the segmented text.
                        </p>
                      </div>
                    </Card>
                  ) : (
                    Object.entries(skillsByCategory).map(([category, skills]) => (
                      <Card
                        key={category}
                        title={category.replace('_', ' ').toUpperCase()}
                        subtitle={`${skills.length} identified skill${skills.length === 1 ? '' : 's'}`}
                      >
                        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
                          {skills.map((skill) => {
                            const isConfirmed = skill.is_user_confirmed;
                            const isInspecting = inspectingSkill?.id === skill.id;

                            return (
                              <div
                                key={skill.id}
                                style={{
                                  display: 'inline-flex',
                                  alignItems: 'center',
                                  gap: '8px',
                                  padding: '6px 12px',
                                  borderRadius: 'var(--radius-full)',
                                  backgroundColor: isConfirmed ? 'var(--success-bg)' : 'var(--slate-100)',
                                  border: isConfirmed ? '1px solid var(--success-border)' : '1px solid var(--slate-200)',
                                  fontSize: '0.8125rem',
                                  color: isConfirmed ? 'var(--success-text)' : 'var(--slate-800)',
                                  transition: 'all 0.15s ease',
                                }}
                              >
                                <span
                                  onClick={() => setInspectingSkill(isInspecting ? null : skill)}
                                  style={{
                                    fontWeight: 600,
                                    cursor: 'pointer',
                                    display: 'inline-flex',
                                    alignItems: 'center',
                                    gap: '6px',
                                  }}
                                  title="Click to inspect evidence snippet"
                                >
                                  {skill.canonical_name}
                                  <Badge
                                    variant={isConfirmed ? 'success' : 'neutral'}
                                    style={{ fontSize: '0.6875rem', padding: '1px 6px' }}
                                  >
                                    {(skill.confidence_score * 100).toFixed(0)}%
                                  </Badge>
                                </span>

                                <button
                                  type="button"
                                  onClick={() => handleToggleConfirmSkill(skill)}
                                  style={{
                                    background: 'none',
                                    border: 'none',
                                    cursor: 'pointer',
                                    color: isConfirmed ? 'var(--success-icon)' : 'var(--slate-400)',
                                    display: 'flex',
                                    alignItems: 'center',
                                    padding: '2px',
                                  }}
                                  title={isConfirmed ? 'Mark unconfirmed' : 'Confirm skill'}
                                >
                                  <Check size={14} strokeWidth={isConfirmed ? 3 : 2} />
                                </button>

                                <button
                                  type="button"
                                  onClick={() => handleDeleteSkill(skill.id, skill.canonical_name)}
                                  style={{
                                    background: 'none',
                                    border: 'none',
                                    cursor: 'pointer',
                                    color: 'var(--slate-400)',
                                    display: 'flex',
                                    alignItems: 'center',
                                    padding: '2px',
                                  }}
                                  title="Remove skill"
                                >
                                  <X size={14} />
                                </button>
                              </div>
                            );
                          })}
                        </div>
                      </Card>
                    ))
                  )}

                  {/* Evidence Snippet Inspector Modal/Callout */}
                  {inspectingSkill && (
                    <div
                      style={{
                        padding: '16px 20px',
                        backgroundColor: 'var(--slate-50)',
                        border: '1px solid var(--slate-300)',
                        borderRadius: 'var(--radius-lg)',
                        display: 'flex',
                        flexDirection: 'column',
                        gap: '8px',
                      }}
                    >
                      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                          <Info size={16} color="var(--primary-600)" />
                          <span style={{ fontWeight: 700, fontSize: '0.875rem', color: 'var(--slate-900)' }}>
                            Evidence Verification: {inspectingSkill.canonical_name}
                          </span>
                        </div>
                        <button
                          type="button"
                          onClick={() => setInspectingSkill(null)}
                          style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--slate-400)' }}
                        >
                          <X size={16} />
                        </button>
                      </div>

                      <div
                        style={{
                          padding: '10px 14px',
                          backgroundColor: '#ffffff',
                          borderRadius: 'var(--radius-md)',
                          border: '1px solid var(--slate-200)',
                          fontSize: '0.8125rem',
                          color: 'var(--slate-700)',
                          fontStyle: 'italic',
                          lineHeight: 1.5,
                        }}
                      >
                        "{inspectingSkill.evidence_snippet || 'No verbatim context snippet available for this skill.'}"
                      </div>

                      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', fontSize: '0.75rem', color: 'var(--slate-500)' }}>
                        <span>
                          Source: {inspectingSkill.is_auto_extracted ? 'Automatic text extraction' : 'User confirmed'}
                        </span>
                        <span>Confidence: {(inspectingSkill.confidence_score * 100).toFixed(0)}%</span>
                      </div>
                    </div>
                  )}
                </div>
              )}

              {/* Tab 2: Segmented Resume Sections */}
              {activeTab === 'sections' && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                  {isLoadingDetails ? (
                    <div style={{ padding: '40px', textAlign: 'center', color: 'var(--slate-500)' }}>
                      Loading parsed sections...
                    </div>
                  ) : !sectionsData?.sections || Object.keys(sectionsData.sections).length === 0 ? (
                    <Card>
                      <div style={{ padding: '32px', textAlign: 'center', color: 'var(--slate-500)' }}>
                        No structured sections segmented in this document.
                      </div>
                    </Card>
                  ) : (
                    Object.entries(sectionsData.sections).map(([sectionKey, sectionContent]) => {
                      const isEditing = editingSectionKey === sectionKey;

                      return (
                        <Card
                          key={sectionKey}
                          title={sectionKey.replace(/_/g, ' ').toUpperCase()}
                          subtitle={`Segmented text block for ${sectionKey}`}
                        >
                          {isEditing ? (
                            <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                              <textarea
                                className="textarea"
                                rows={6}
                                value={editingSectionText}
                                onChange={(e) => setEditingSectionText(e.target.value)}
                                style={{ fontFamily: 'var(--font-mono)', fontSize: '0.8125rem', lineHeight: 1.5 }}
                              />
                              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'flex-end', gap: '8px' }}>
                                <Button
                                  size="sm"
                                  variant="outline"
                                  onClick={() => setEditingSectionKey(null)}
                                >
                                  Cancel
                                </Button>
                                <Button
                                  size="sm"
                                  variant="primary"
                                  isLoading={isSavingSection}
                                  onClick={() => handleSaveSection(sectionKey)}
                                  icon={<Save size={14} />}
                                >
                                  Save Section
                                </Button>
                              </div>
                            </div>
                          ) : (
                            <div>
                              <div
                                style={{
                                  padding: '12px 14px',
                                  backgroundColor: 'var(--slate-50)',
                                  borderRadius: 'var(--radius-md)',
                                  border: '1px solid var(--slate-200)',
                                  fontSize: '0.8125rem',
                                  color: 'var(--slate-700)',
                                  whiteSpace: 'pre-wrap',
                                  lineHeight: 1.6,
                                  maxHeight: '220px',
                                  overflowY: 'auto',
                                }}
                              >
                                {sectionContent || '(Empty section)'}
                              </div>
                              <div style={{ marginTop: '10px', display: 'flex', justifyContent: 'flex-end' }}>
                                <Button
                                  size="sm"
                                  variant="outline"
                                  onClick={() => handleStartEditSection(sectionKey, sectionContent)}
                                  icon={<Edit2 size={14} />}
                                >
                                  Edit Section Content
                                </Button>
                              </div>
                            </div>
                          )}
                        </Card>
                      );
                    })
                  )}
                </div>
              )}
            </>
          ) : (
            <Card title="No Resume Selected" subtitle="Select a resume from the list or upload a new file">
              <div style={{ padding: '48px 24px', textAlign: 'center', color: 'var(--slate-500)' }}>
                <FileText size={36} color="var(--slate-300)" style={{ margin: '0 auto 12px' }} />
                <p style={{ margin: 0, fontWeight: 500 }}>Select a resume from the left panel to inspect parsed skills and sections.</p>
              </div>
            </Card>
          )}
        </div>
      </div>
    </div>
  );
};
