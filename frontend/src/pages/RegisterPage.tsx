import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import {
  Compass,
  Lock,
  Mail,
  Eye,
  EyeOff,
  AlertCircle,
  Check,
  ShieldCheck,
  ArrowRight,
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { useAlert } from '../context/AlertContext';
import { api } from '../services/api';
import { TokenResponse } from '../types';
import { Button } from '../components/common/Button';

interface PasswordScore {
  strength: 'weak' | 'medium' | 'strong';
  score: number;
  label: string;
  color: string;
}

function evaluatePassword(password: string): PasswordScore {
  if (!password) {
    return { strength: 'weak', score: 0, label: 'Too short', color: 'var(--slate-300)' };
  }
  let score = 0;
  if (password.length >= 8) score += 1;
  if (password.length >= 12) score += 1;
  if (/[0-9]/.test(password)) score += 1;
  if (/[a-z]/.test(password) && /[A-Z]/.test(password)) score += 1;
  if (/[^A-Za-z0-9]/.test(password)) score += 1;

  if (score <= 2) {
    return { strength: 'weak', score: 33, label: 'Weak', color: 'var(--danger-500)' };
  } else if (score <= 4) {
    return { strength: 'medium', score: 66, label: 'Moderate', color: 'var(--warning-500)' };
  } else {
    return { strength: 'strong', score: 100, label: 'Strong', color: 'var(--success-500)' };
  }
}

export const RegisterPage: React.FC = () => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [ackDisclaimer, setAckDisclaimer] = useState(false);
  const [consentAnalytics, setConsentAnalytics] = useState(true);
  const [isLoading, setIsLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const { login } = useAuth();
  const { showAlert } = useAlert();
  const navigate = useNavigate();

  const passwordEvaluation = evaluatePassword(password);
  const passwordsMatch = confirmPassword.length > 0 && password === confirmPassword;
  const passwordsMismatch = confirmPassword.length > 0 && password !== confirmPassword;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMessage(null);

    const cleanEmail = email.trim().toLowerCase();
    if (!cleanEmail) {
      setErrorMessage('Please enter a valid email address.');
      return;
    }

    if (password.length < 8) {
      setErrorMessage('Password must be at least 8 characters long.');
      return;
    }

    if (password !== confirmPassword) {
      setErrorMessage('Passwords do not match. Please verify.');
      return;
    }

    if (!ackDisclaimer) {
      setErrorMessage('You must acknowledge the non-hiring educational disclaimer to continue.');
      return;
    }

    setIsLoading(true);

    try {
      // 1. Register candidate account
      await api.post('/auth/register', {
        email: cleanEmail,
        password,
      });

      // 2. Automatically log in to establish session
      const tokenData = await api.post<TokenResponse>('/auth/login', {
        email: cleanEmail,
        password,
      });

      await login(tokenData.access_token);

      // If user opted into or out of analytics during registration, sync immediately
      if (!consentAnalytics) {
        try {
          await api.put('/profile', { consent_analytics: false });
        } catch {
          // Non-blocking
        }
      }

      showAlert('Account successfully registered! Welcome to CareerPilot.', 'success');
      // Direct new user immediately into onboarding
      navigate('/onboarding');
    } catch (err: any) {
      const msg =
        err?.data?.error?.message ||
        err?.data?.detail?.message ||
        (typeof err?.data?.detail === 'string' ? err.data.detail : null) ||
        err?.message ||
        'Registration failed. This email may already be registered.';
      setErrorMessage(msg);
      showAlert(msg, 'danger');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div
      style={{
        minHeight: '100vh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        backgroundColor: 'var(--slate-100)',
        padding: '24px',
      }}
    >
      <div
        style={{
          width: '100%',
          maxWidth: '460px',
          background: '#ffffff',
          borderRadius: 'var(--radius-xl)',
          boxShadow: 'var(--shadow-xl)',
          padding: '40px 32px 32px',
          border: '1px solid var(--slate-200)',
        }}
      >
        {/* Brand Header */}
        <div style={{ textAlign: 'center', marginBottom: '24px' }}>
          <div
            style={{
              width: '52px',
              height: '52px',
              borderRadius: '14px',
              background: 'linear-gradient(135deg, var(--primary-600), var(--primary-800))',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: '#ffffff',
              margin: '0 auto 14px',
              boxShadow: '0 4px 12px rgba(37, 99, 235, 0.25)',
            }}
          >
            <Compass size={30} />
          </div>
          <h2 style={{ fontSize: '1.5rem', fontWeight: 800, color: 'var(--slate-900)', margin: 0 }}>
            Create Your Account
          </h2>
          <p style={{ color: 'var(--slate-500)', fontSize: '0.875rem', marginTop: '6px' }}>
            Diagnostic Placement Readiness & Rubric Coaching
          </p>
        </div>

        {/* Local Error Alert */}
        {errorMessage && (
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '10px',
              padding: '12px 14px',
              borderRadius: 'var(--radius-md)',
              backgroundColor: 'var(--danger-50)',
              border: '1px solid var(--danger-200)',
              color: 'var(--danger-700)',
              fontSize: '0.8125rem',
              marginBottom: '20px',
            }}
          >
            <AlertCircle size={16} style={{ flexShrink: 0 }} />
            <span>{errorMessage}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          {/* Email */}
          <div>
            <label
              htmlFor="reg-email"
              style={{
                display: 'block',
                fontSize: '0.8125rem',
                fontWeight: 600,
                color: 'var(--slate-700)',
                marginBottom: '6px',
              }}
            >
              Email Address
            </label>
            <div style={{ position: 'relative' }}>
              <Mail
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
                id="reg-email"
                type="email"
                required
                autoComplete="email"
                className="input"
                style={{ paddingLeft: '38px' }}
                placeholder="candidate@university.edu"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
              />
            </div>
          </div>

          {/* Password */}
          <div>
            <label
              htmlFor="reg-password"
              style={{
                display: 'block',
                fontSize: '0.8125rem',
                fontWeight: 600,
                color: 'var(--slate-700)',
                marginBottom: '6px',
              }}
            >
              Password
            </label>
            <div style={{ position: 'relative' }}>
              <Lock
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
                id="reg-password"
                type={showPassword ? 'text' : 'password'}
                required
                autoComplete="new-password"
                className="input"
                style={{ paddingLeft: '38px', paddingRight: '40px' }}
                placeholder="Minimum 8 characters"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                style={{
                  position: 'absolute',
                  right: '10px',
                  top: '50%',
                  transform: 'translateY(-50%)',
                  background: 'none',
                  border: 'none',
                  cursor: 'pointer',
                  color: 'var(--slate-400)',
                  display: 'flex',
                  alignItems: 'center',
                  padding: '4px',
                }}
                title={showPassword ? 'Hide password' : 'Show password'}
              >
                {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
              </button>
            </div>

            {/* Password Strength Indicator */}
            {password.length > 0 && (
              <div style={{ marginTop: '8px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', marginBottom: '4px' }}>
                  <span style={{ color: 'var(--slate-500)' }}>Password Strength:</span>
                  <span style={{ fontWeight: 600, color: passwordEvaluation.color }}>
                    {passwordEvaluation.label}
                  </span>
                </div>
                <div
                  style={{
                    height: '4px',
                    width: '100%',
                    backgroundColor: 'var(--slate-200)',
                    borderRadius: '2px',
                    overflow: 'hidden',
                  }}
                >
                  <div
                    style={{
                      height: '100%',
                      width: `${passwordEvaluation.score}%`,
                      backgroundColor: passwordEvaluation.color,
                      transition: 'all 0.3s ease',
                    }}
                  />
                </div>
              </div>
            )}
          </div>

          {/* Confirm Password */}
          <div>
            <label
              htmlFor="reg-confirm-password"
              style={{
                display: 'block',
                fontSize: '0.8125rem',
                fontWeight: 600,
                color: 'var(--slate-700)',
                marginBottom: '6px',
              }}
            >
              Confirm Password
            </label>
            <div style={{ position: 'relative' }}>
              <Lock
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
                id="reg-confirm-password"
                type={showPassword ? 'text' : 'password'}
                required
                autoComplete="new-password"
                className="input"
                style={{
                  paddingLeft: '38px',
                  paddingRight: '38px',
                  borderColor: passwordsMismatch
                    ? 'var(--danger-500)'
                    : passwordsMatch
                    ? 'var(--success-500)'
                    : undefined,
                }}
                placeholder="Repeat password"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
              />
              {passwordsMatch && (
                <Check
                  size={16}
                  style={{
                    position: 'absolute',
                    right: '12px',
                    top: '50%',
                    transform: 'translateY(-50%)',
                    color: 'var(--success-600)',
                  }}
                />
              )}
            </div>
            {passwordsMismatch && (
              <p style={{ fontSize: '0.75rem', color: 'var(--danger-600)', margin: '4px 0 0' }}>
                Passwords do not match.
              </p>
            )}
          </div>

          {/* Statutory Ethical Acknowledgment (Mandatory) */}
          <div
            style={{
              padding: '12px 14px',
              borderRadius: 'var(--radius-md)',
              backgroundColor: 'var(--warning-50)',
              border: '1px solid var(--warning-200)',
              marginTop: '4px',
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
                required
                checked={ackDisclaimer}
                onChange={(e) => setAckDisclaimer(e.target.checked)}
                style={{ marginTop: '3px', width: '16px', height: '16px', cursor: 'pointer' }}
              />
              <div style={{ fontSize: '0.75rem', color: 'var(--warning-900)', lineHeight: 1.45 }}>
                <span style={{ fontWeight: 700, display: 'inline-flex', alignItems: 'center', gap: '4px' }}>
                  <ShieldCheck size={14} color="var(--warning-700)" />
                  Ethical Practice Acknowledgment:
                </span>{' '}
                I understand CareerPilot AI is an educational coaching tool. It{' '}
                <strong>does not predict hiring decisions, guarantee interviews, or promise job placement.</strong>
              </div>
            </label>
          </div>

          {/* Telemetry Consent (Optional) */}
          <div>
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
                style={{ marginTop: '2px', width: '15px', height: '15px', cursor: 'pointer' }}
              />
              <span style={{ fontSize: '0.75rem', color: 'var(--slate-600)', lineHeight: 1.4 }}>
                Consent to aggregate placement telemetry (study streaks & topic mastery calculations). No commercial data sharing.
              </span>
            </label>
          </div>

          <Button
            type="submit"
            variant="primary"
            isLoading={isLoading}
            disabled={!ackDisclaimer}
            style={{ width: '100%', marginTop: '8px', justifyContent: 'center' }}
            icon={<ArrowRight size={16} />}
          >
            Create Account & Continue
          </Button>
        </form>

        <div
          style={{
            marginTop: '22px',
            textAlign: 'center',
            fontSize: '0.8125rem',
            color: 'var(--slate-500)',
          }}
        >
          Already have an account?{' '}
          <Link
            to="/login"
            style={{ color: 'var(--primary-600)', fontWeight: 600, textDecoration: 'none' }}
          >
            Sign In
          </Link>
        </div>
      </div>
    </div>
  );
};
