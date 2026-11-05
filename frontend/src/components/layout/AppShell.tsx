import React, { useState } from 'react';
import { NavLink, Outlet, useNavigate } from 'react-router-dom';
import {
  Briefcase,
  CheckCircle,
  FileText,
  LayoutDashboard,
  LogOut,
  Menu,
  MessageSquare,
  TrendingUp,
  X,
  Compass,
} from 'lucide-react';
import { useAuth } from '../../context/AuthContext';
import { Badge } from '../common/Badge';

export const AppShell: React.FC = () => {
  const { user, profile, logout } = useAuth();
  const navigate = useNavigate();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  const navItems = [
    { label: 'Dashboard', to: '/dashboard', icon: <LayoutDashboard size={18} /> },
    { label: 'Resume Workspace', to: '/resumes', icon: <FileText size={18} /> },
    { label: 'Job Matching', to: '/matching', icon: <Briefcase size={18} /> },
    { label: 'Diagnostic Practice', to: '/practice', icon: <CheckCircle size={18} /> },
    { label: 'Mock Interviews', to: '/interviews', icon: <MessageSquare size={18} /> },
    { label: 'Progress & Telemetry', to: '/progress', icon: <TrendingUp size={18} /> },
  ];

  return (
    <div className="app-container">
      {/* Sidebar Navigation */}
      <aside className={`sidebar ${mobileMenuOpen ? 'open' : ''}`}>
        <div
          style={{
            padding: '20px 24px',
            borderBottom: '1px solid var(--slate-800)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <div
              style={{
                width: '36px',
                height: '36px',
                borderRadius: '8px',
                background: 'linear-gradient(135deg, var(--primary-500), var(--primary-700))',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: '#ffffff',
              }}
            >
              <Compass size={22} />
            </div>
            <div>
              <span style={{ fontSize: '1.125rem', fontWeight: 700, letterSpacing: '-0.02em' }}>
                CareerPilot AI
              </span>
              <span
                style={{
                  display: 'block',
                  fontSize: '0.6875rem',
                  color: 'var(--slate-400)',
                  fontWeight: 500,
                  textTransform: 'uppercase',
                  letterSpacing: '0.05em',
                }}
              >
                Placement Intelligence
              </span>
            </div>
          </div>
          {mobileMenuOpen && (
            <button
              onClick={() => setMobileMenuOpen(false)}
              style={{ background: 'none', border: 'none', color: '#ffffff', cursor: 'pointer' }}
              aria-label="Close menu"
            >
              <X size={20} />
            </button>
          )}
        </div>

        {/* Current Target Role Pill */}
        <div style={{ padding: '16px 24px', borderBottom: '1px solid var(--slate-800)' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
            <span style={{ fontSize: '0.75rem', color: 'var(--slate-400)' }}>
              Active Target Role
            </span>
            <NavLink
              to="/onboarding"
              style={{ fontSize: '0.6875rem', color: 'var(--primary-400)', textDecoration: 'none', fontWeight: 600 }}
              onClick={() => setMobileMenuOpen(false)}
            >
              Edit
            </NavLink>
          </div>
          <NavLink
            to="/onboarding"
            style={{ textDecoration: 'none', display: 'block' }}
            onClick={() => setMobileMenuOpen(false)}
          >
            <Badge variant="primary" className="text-truncate" style={{ maxWidth: '100%', cursor: 'pointer' }}>
              {profile?.target_role || 'Junior Python Developer'}
            </Badge>
          </NavLink>
        </div>

        {/* Nav Links */}
        <nav style={{ padding: '16px 12px', flex: 1, overflowY: 'auto' }}>
          {navItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              onClick={() => setMobileMenuOpen(false)}
              className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}
            >
              {item.icon}
              <span>{item.label}</span>
            </NavLink>
          ))}
        </nav>

        {/* User Card & Logout */}
        <div
          style={{
            padding: '16px 20px',
            borderTop: '1px solid var(--slate-800)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
          }}
        >
          <div style={{ overflow: 'hidden' }}>
            <span
              style={{
                display: 'block',
                fontSize: '0.8125rem',
                fontWeight: 600,
                color: '#ffffff',
                textOverflow: 'ellipsis',
                overflow: 'hidden',
                whiteSpace: 'nowrap',
              }}
            >
              {user?.email || 'student@example.com'}
            </span>
            <span style={{ fontSize: '0.6875rem', color: 'var(--slate-400)' }}>
              Candidate Account
            </span>
          </div>
          <button
            onClick={handleLogout}
            style={{
              background: 'none',
              border: 'none',
              color: 'var(--slate-400)',
              cursor: 'pointer',
              padding: '6px',
              borderRadius: 'var(--radius-sm)',
              display: 'flex',
              alignItems: 'center',
            }}
            title="Sign out"
            aria-label="Sign out"
          >
            <LogOut size={18} />
          </button>
        </div>
      </aside>

      {/* Main Viewport Container */}
      <div className="main-content">
        {/* Top Header */}
        <header className="header">
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <button
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              style={{
                display: 'none',
                background: 'none',
                border: 'none',
                cursor: 'pointer',
                color: 'var(--slate-700)',
              }}
              className="mobile-toggle"
              aria-label="Toggle navigation menu"
            >
              <Menu size={22} />
            </button>
            <h1 style={{ fontSize: '1.25rem', fontWeight: 600, color: 'var(--slate-900)' }}>
              Placement Intelligence Suite
            </h1>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
            <Badge variant="success">System Online (Local Engine)</Badge>
          </div>
        </header>

        {/* Page Content Viewport */}
        <main className="page-body">
          <Outlet />
        </main>

        {/* Ethical Disclaimer Footer */}
        <footer className="footer-disclosure">
          <p>
            <strong>CareerPilot AI:</strong> This platform provides automated content relevance scores and
            structured rubric coaching. It does not predict interview callbacks or hiring outcomes, nor guarantee
            placement. Evaluation scores are deterministic and explainable without biometric or personality inference.
          </p>
        </footer>
      </div>
    </div>
  );
};
