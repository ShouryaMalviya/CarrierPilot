import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Compass,
  CheckCircle2,
  ShieldCheck,
  Briefcase,
  Globe,
  BarChart2,
  Info,
  ArrowRight,
  Sparkles,
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { useAlert } from '../context/AlertContext';
import { api } from '../services/api';
import { OnboardingDisclosure } from '../types';
import { Button } from '../components/common/Button';
import { Card } from '../components/common/Card';
import { Badge } from '../components/common/Badge';

const FALLBACK_ROLES = [
  'Junior Python Developer',
  'Associate Frontend Developer',
  'Entry-Level Data/ML Analyst',
  'Backend Engineer',
  'Full-Stack Developer',
  'DevOps & Cloud Engineer',
];

const SUPPORTED_LANGUAGES = [
  { code: 'English', label: 'English (US / UK / Global)' },
  { code: 'Spanish', label: 'Español (Spanish)' },
  { code: 'French', label: 'Français (French)' },
  { code: 'German', label: 'Deutsch (German)' },
  { code: 'Hindi', label: 'हिन्दी (Hindi)' },
  { code: 'Japanese', label: '日本語 (Japanese)' },
];

export const OnboardingPage: React.FC = () => {
  const { profile, updateProfile, refreshProfile } = useAuth();
  const { showAlert } = useAlert();
  const navigate = useNavigate();

  const [roles, setRoles] = useState<string[]>(FALLBACK_ROLES);
  const [selectedRole, setSelectedRole] = useState<string>(
    profile?.target_role || 'Junior Python Developer'
  );
  const [customRole, setCustomRole] = useState<string>('');
  const [isCustom, setIsCustom] = useState<boolean>(false);
  const [language, setLanguage] = useState<string>(profile?.preferred_language || 'English');
  const [consentAnalytics, setConsentAnalytics] = useState<boolean>(
    profile?.consent_analytics ?? true
  );
  const [disclosure, setDisclosure] = useState<OnboardingDisclosure | null>(null);
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const [isLoading, setIsLoading] = useState<boolean>(true);

  useEffect(() => {
    const fetchOnboardingData = async () => {
      try {
        const [rolesRes, infoRes] = await Promise.all([
          api.get<string[]>('/profile/roles').catch(() => FALLBACK_ROLES),
          api.get<OnboardingDisclosure>('/profile/onboarding-info').catch(() => null),
        ]);
        if (rolesRes && rolesRes.length > 0) {
          setRoles(rolesRes);
        }
        if (infoRes) {
          setDisclosure(infoRes);
        }
      } catch {
        // Fallbacks already set
      } finally {
        setIsLoading(false);
      }
    };

    fetchOnboardingData();
  }, []);

  useEffect(() => {
    if (profile) {
      if (roles.includes(profile.target_role)) {
        setSelectedRole(profile.target_role);
        setIsCustom(false);
      } else if (profile.target_role) {
        setSelectedRole('custom');
        setCustomRole(profile.target_role);
        setIsCustom(true);
      }
      if (profile.preferred_language) {
        setLanguage(profile.preferred_language);
      }
      if (profile.consent_analytics !== undefined) {
        setConsentAnalytics(profile.consent_analytics);
      }
    }
  }, [profile, roles]);

  const handleRoleSelect = (role: string) => {
    if (role === 'custom') {
      setIsCustom(true);
      setSelectedRole('custom');
    } else {
      setIsCustom(false);
      setSelectedRole(role);
      setCustomRole('');
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const finalRole = isCustom ? customRole.trim() : selectedRole.trim();

    if (!finalRole || finalRole.length < 2) {
      showAlert('Please choose or enter a valid target role (min 2 characters).', 'warning');
      return;
    }

    setIsSubmitting(true);
    try {
      await updateProfile({
        target_role: finalRole,
        preferred_language: language,
        consent_analytics: consentAnalytics,
      });
      await refreshProfile();
      showAlert('Career profile and onboarding preferences saved successfully!', 'success');
      navigate('/dashboard');
    } catch (err: any) {
      showAlert(err.message || 'Failed to save onboarding preferences.', 'danger');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div
      style={{
        maxWidth: '860px',
        margin: '0 auto',
        padding: '32px 16px 64px',
      }}
    >
      {/* Header Banner */}
      <div
        style={{
          background: 'linear-gradient(135deg, var(--primary-700), var(--primary-900))',
          borderRadius: 'var(--radius-xl)',
          padding: '36px 32px',
          color: '#ffffff',
          marginBottom: '32px',
          boxShadow: 'var(--shadow-md)',
          position: 'relative',
          overflow: 'hidden',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '16px', marginBottom: '12px' }}>
          <div
            style={{
              width: '44px',
              height: '44px',
              borderRadius: '12px',
              backgroundColor: 'rgba(255, 255, 255, 0.15)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}
          >
            <Compass size={26} color="#ffffff" />
          </div>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span style={{ fontSize: '0.8125rem', textTransform: 'uppercase', letterSpacing: '0.08em', opacity: 0.85, fontWeight: 700 }}>
                Candidate Onboarding
              </span>
              <Badge variant="neutral">Step 1 of 1</Badge>
            </div>
            <h1 style={{ fontSize: '1.75rem', fontWeight: 800, margin: '2px 0 0', color: '#ffffff' }}>
              Configure Your Placement Profile
            </h1>
          </div>
        </div>
        <p style={{ fontSize: '0.9375rem', opacity: 0.9, maxWidth: '640px', lineHeight: 1.6, margin: 0 }}>
          {disclosure?.purpose ||
            'CareerPilot AI tailors diagnostic practice questions, resume matching analysis, and mock interview prompts to your target career role.'}
        </p>
      </div>

      <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '28px' }}>
        {/* Step 1: Target Role Selection */}
        <Card
          title="1. Select Target Job Role"
          subtitle="All curriculum recommendations and interview competencies align with this role."
        >
          <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
            <div
              style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fill, minmax(240px, 1fr))',
                gap: '12px',
              }}
            >
              {roles.map((role) => {
                const isSelected = !isCustom && selectedRole === role;
                return (
                  <button
                    key={role}
                    type="button"
                    onClick={() => handleRoleSelect(role)}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: '12px',
                      padding: '14px 16px',
                      borderRadius: 'var(--radius-md)',
                      border: isSelected
                        ? '2px solid var(--primary-600)'
                        : '1px solid var(--slate-200)',
                      backgroundColor: isSelected ? 'var(--primary-50)' : '#ffffff',
                      color: isSelected ? 'var(--primary-900)' : 'var(--slate-800)',
                      cursor: 'pointer',
                      textAlign: 'left',
                      fontWeight: isSelected ? 600 : 500,
                      transition: 'var(--transition-fast)',
                    }}
                  >
                    <Briefcase
                      size={18}
                      color={isSelected ? 'var(--primary-600)' : 'var(--slate-400)'}
                    />
                    <span style={{ flex: 1, fontSize: '0.875rem' }}>{role}</span>
                    {isSelected && <CheckCircle2 size={18} color="var(--primary-600)" />}
                  </button>
                );
              })}

              {/* Custom Role Option */}
              <button
                type="button"
                onClick={() => handleRoleSelect('custom')}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '12px',
                  padding: '14px 16px',
                  borderRadius: 'var(--radius-md)',
                  border: isCustom
                    ? '2px solid var(--primary-600)'
                    : '1px dashed var(--slate-300)',
                  backgroundColor: isCustom ? 'var(--primary-50)' : '#ffffff',
                  color: isCustom ? 'var(--primary-900)' : 'var(--slate-700)',
                  cursor: 'pointer',
                  textAlign: 'left',
                  fontWeight: isCustom ? 600 : 500,
                  transition: 'var(--transition-fast)',
                }}
              >
                <Sparkles
                  size={18}
                  color={isCustom ? 'var(--primary-600)' : 'var(--slate-400)'}
                />
                <span style={{ flex: 1, fontSize: '0.875rem' }}>Other / Custom Role...</span>
                {isCustom && <CheckCircle2 size={18} color="var(--primary-600)" />}
              </button>
            </div>

            {isCustom && (
              <div
                style={{
                  padding: '16px',
                  backgroundColor: 'var(--slate-50)',
                  borderRadius: 'var(--radius-md)',
                  border: '1px solid var(--slate-200)',
                  marginTop: '8px',
                }}
              >
                <label
                  htmlFor="custom-role-input"
                  style={{
                    display: 'block',
                    fontSize: '0.8125rem',
                    fontWeight: 600,
                    color: 'var(--slate-700)',
                    marginBottom: '6px',
                  }}
                >
                  Enter Custom Role Title
                </label>
                <input
                  id="custom-role-input"
                  type="text"
                  className="input"
                  placeholder="e.g. SRE / Cloud Architect, Mobile Android Engineer"
                  value={customRole}
                  onChange={(e) => setCustomRole(e.target.value)}
                  maxLength={100}
                  required={isCustom}
                  autoFocus
                />
                <p style={{ fontSize: '0.75rem', color: 'var(--slate-500)', marginTop: '4px' }}>
                  We will calibrate diagnostic question difficulty and skill matching against this designation.
                </p>
              </div>
            )}
          </div>
        </Card>

        {/* Step 2: Language & Telemetry Preferences */}
        <Card
          title="2. Interface & Analytics Preferences"
          subtitle="Customize your learning environment and feedback telemetry."
        >
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '20px' }}>
            <div>
              <label
                htmlFor="language-select"
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px',
                  fontSize: '0.8125rem',
                  fontWeight: 600,
                  color: 'var(--slate-700)',
                  marginBottom: '6px',
                }}
              >
                <Globe size={16} /> Preferred Communication Language
              </label>
              <select
                id="language-select"
                className="input"
                value={language}
                onChange={(e) => setLanguage(e.target.value)}
              >
                {SUPPORTED_LANGUAGES.map((lang) => (
                  <option key={lang.code} value={lang.code}>
                    {lang.label}
                  </option>
                ))}
              </select>
              <p style={{ fontSize: '0.75rem', color: 'var(--slate-500)', marginTop: '4px' }}>
                Coaching summaries and UI feedback prompts will adhere to this preference where available.
              </p>
            </div>

            <div
              style={{
                display: 'flex',
                flexDirection: 'column',
                justifyContent: 'center',
                padding: '14px',
                borderRadius: 'var(--radius-md)',
                backgroundColor: 'var(--slate-50)',
                border: '1px solid var(--slate-200)',
              }}
            >
              <label
                style={{
                  display: 'flex',
                  alignItems: 'flex-start',
                  gap: '10px',
                  cursor: 'pointer',
                  userSelect: 'none',
                }}
              >
                <input
                  type="checkbox"
                  checked={consentAnalytics}
                  onChange={(e) => setConsentAnalytics(e.target.checked)}
                  style={{ marginTop: '3px', width: '16px', height: '16px', cursor: 'pointer' }}
                />
                <div>
                  <div
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: '6px',
                      fontSize: '0.875rem',
                      fontWeight: 600,
                      color: 'var(--slate-800)',
                    }}
                  >
                    <BarChart2 size={16} color="var(--primary-600)" />
                    Placement Readiness Telemetry
                  </div>
                  <p style={{ fontSize: '0.75rem', color: 'var(--slate-500)', margin: '4px 0 0', lineHeight: 1.4 }}>
                    Allow aggregate calculation of 14-day study streaks and topic mastery indices. No third-party data sharing.
                  </p>
                </div>
              </label>
            </div>
          </div>
        </Card>

        {/* Step 3: Ethical Transparency & Product Disclosures */}
        <Card
          title="3. Ethical Transparency & Disclosures"
          subtitle="Non-negotiable product principles and statutory user rights."
        >
          <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
            <div
              style={{
                display: 'flex',
                alignItems: 'flex-start',
                gap: '12px',
                padding: '14px 16px',
                borderRadius: 'var(--radius-md)',
                backgroundColor: 'var(--warning-50)',
                border: '1px solid var(--warning-200)',
              }}
            >
              <ShieldCheck size={20} color="var(--warning-600)" style={{ flexShrink: 0, marginTop: '2px' }} />
              <div>
                <div style={{ fontSize: '0.875rem', fontWeight: 700, color: 'var(--warning-900)' }}>
                  Non-Hiring & Non-Placement Guarantee Disclaimer
                </div>
                <ul
                  style={{
                    fontSize: '0.8125rem',
                    color: 'var(--warning-800)',
                    margin: '6px 0 0',
                    paddingLeft: '18px',
                    lineHeight: 1.5,
                  }}
                >
                  {(disclosure?.disclaimers || [
                    'CareerPilot AI is an educational coaching tool, not an employment agency or recruiter.',
                    'Matching scores indicate curriculum alignment and keyword coverage; they are not hiring probabilities.',
                    'CareerPilot AI does not predict hiring decisions, nor does it guarantee employment or placement.',
                  ]).map((item, idx) => (
                    <li key={idx} style={{ marginBottom: '4px' }}>
                      {item}
                    </li>
                  ))}
                </ul>
              </div>
            </div>

            <div
              style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))',
                gap: '12px',
                fontSize: '0.8125rem',
              }}
            >
              <div
                style={{
                  padding: '12px 14px',
                  borderRadius: 'var(--radius-md)',
                  backgroundColor: 'var(--slate-50)',
                  border: '1px solid var(--slate-200)',
                }}
              >
                <div style={{ fontWeight: 600, color: 'var(--slate-800)', display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '4px' }}>
                  <Info size={14} color="var(--primary-600)" />
                  Camera & Audio Policy
                </div>
                <div style={{ color: 'var(--slate-600)', lineHeight: 1.4 }}>
                  Camera and microphone are <strong>never required</strong>. All mock interview sessions operate via structured typed candidate responses.
                </div>
              </div>

              <div
                style={{
                  padding: '12px 14px',
                  borderRadius: 'var(--radius-md)',
                  backgroundColor: 'var(--slate-50)',
                  border: '1px solid var(--slate-200)',
                }}
              >
                <div style={{ fontWeight: 600, color: 'var(--slate-800)', display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '4px' }}>
                  <ShieldCheck size={14} color="var(--success-600)" />
                  Data Ownership & Privacy
                </div>
                <div style={{ color: 'var(--slate-600)', lineHeight: 1.4 }}>
                  {disclosure?.data_retention_policy ||
                    'Your resume and practice history are stored securely and privately. You retain full control to edit or delete your data at any time.'}
                </div>
              </div>
            </div>
          </div>
        </Card>

        {/* Action Controls */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            paddingTop: '8px',
          }}
        >
          <Button
            type="button"
            variant="outline"
            onClick={() => navigate('/dashboard')}
          >
            Skip for Now
          </Button>

          <Button
            type="submit"
            variant="primary"
            isLoading={isSubmitting || isLoading}
            icon={<ArrowRight size={16} />}
          >
            Save Preferences & Launch Dashboard
          </Button>
        </div>
      </form>
    </div>
  );
};
