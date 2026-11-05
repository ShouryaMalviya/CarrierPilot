import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Compass, Lock, Mail, Eye, EyeOff, AlertCircle, ArrowRight } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { useAlert } from '../context/AlertContext';
import { api } from '../services/api';
import { TokenResponse } from '../types';
import { Button } from '../components/common/Button';

export const LoginPage: React.FC = () => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const { login } = useAuth();
  const { showAlert } = useAlert();
  const navigate = useNavigate();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMessage(null);

    const cleanEmail = email.trim().toLowerCase();
    if (!cleanEmail) {
      setErrorMessage('Please enter your email address.');
      return;
    }

    if (!password) {
      setErrorMessage('Please enter your password.');
      return;
    }

    setIsLoading(true);

    try {
      const data = await api.post<TokenResponse>('/auth/login', {
        email: cleanEmail,
        password,
      });

      await login(data.access_token);
      showAlert('Welcome back! Successfully signed in.', 'success');
      navigate('/dashboard');
    } catch (err: any) {
      const msg =
        err?.data?.error?.message ||
        err?.data?.detail?.message ||
        (typeof err?.data?.detail === 'string' ? err.data.detail : null) ||
        err?.message ||
        'Authentication failed. Please verify your credentials.';
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
          maxWidth: '440px',
          background: '#ffffff',
          borderRadius: 'var(--radius-xl)',
          boxShadow: 'var(--shadow-xl)',
          padding: '40px 32px 32px',
          border: '1px solid var(--slate-200)',
        }}
      >
        {/* Brand Header */}
        <div style={{ textAlign: 'center', marginBottom: '28px' }}>
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
            Sign In to CareerPilot
          </h2>
          <p style={{ color: 'var(--slate-500)', fontSize: '0.875rem', marginTop: '6px' }}>
            Adaptive Diagnostic Practice & Interview Coaching
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

        <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '18px' }}>
          <div>
            <label
              htmlFor="login-email"
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
                id="login-email"
                type="email"
                required
                autoComplete="email"
                className="input"
                style={{ paddingLeft: '38px' }}
                placeholder="candidate@example.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
              />
            </div>
          </div>

          <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
              <label
                htmlFor="login-password"
                style={{
                  fontSize: '0.8125rem',
                  fontWeight: 600,
                  color: 'var(--slate-700)',
                }}
              >
                Password
              </label>
            </div>
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
                id="login-password"
                type={showPassword ? 'text' : 'password'}
                required
                autoComplete="current-password"
                className="input"
                style={{ paddingLeft: '38px', paddingRight: '40px' }}
                placeholder="••••••••••••"
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
          </div>

          <Button
            type="submit"
            variant="primary"
            isLoading={isLoading}
            style={{ width: '100%', marginTop: '6px', justifyContent: 'center' }}
            icon={<ArrowRight size={16} />}
          >
            Sign In
          </Button>
        </form>

        <div
          style={{
            marginTop: '24px',
            textAlign: 'center',
            fontSize: '0.8125rem',
            color: 'var(--slate-500)',
          }}
        >
          Don't have an account?{' '}
          <Link
            to="/register"
            style={{ color: 'var(--primary-600)', fontWeight: 600, textDecoration: 'none' }}
          >
            Create Candidate Account
          </Link>
        </div>

        {/* Ethical Disclaimer Footer */}
        <div
          style={{
            marginTop: '28px',
            paddingTop: '16px',
            borderTop: '1px solid var(--slate-100)',
            fontSize: '0.6875rem',
            color: 'var(--slate-400)',
            lineHeight: 1.4,
            textAlign: 'center',
          }}
        >
          CareerPilot AI is an educational coaching assistant. It does not predict hiring decisions nor guarantee employment.
        </div>
      </div>
    </div>
  );
};
