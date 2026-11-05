import React from 'react';
import { Card } from '../components/common/Card';
import { EthicalDisclaimerBanner } from '../components/common/EthicalDisclaimerBanner';
import { useAuth } from '../context/AuthContext';

export const DashboardPage: React.FC = () => {
  const { profile } = useAuth();

  return (
    <div>
      <EthicalDisclaimerBanner />
      <div style={{ marginBottom: '24px' }}>
        <h2 style={{ fontSize: '1.5rem', fontWeight: 700, color: 'var(--slate-900)' }}>
          Candidate Placement Overview
        </h2>
        <p style={{ color: 'var(--slate-500)', fontSize: '0.875rem' }}>
          Real-time readiness telemetry, daily practice habits, and job alignment diagnostics.
        </p>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '20px' }}>
        <Card title="Placement Readiness Index" subtitle="Multi-factor preparation score">
          <div style={{ padding: '16px 0', textAlign: 'center' }}>
            <span style={{ fontSize: '2.5rem', fontWeight: 700, color: 'var(--primary-600)' }}>
              --%
            </span>
            <p style={{ fontSize: '0.8125rem', color: 'var(--slate-500)', marginTop: '4px' }}>
              Upload resume and complete diagnostic sessions to compute score
            </p>
          </div>
        </Card>

        <Card title="Practice Streak" subtitle="Daily consistency tracking">
          <div style={{ padding: '16px 0', textAlign: 'center' }}>
            <span style={{ fontSize: '2.5rem', fontWeight: 700, color: 'var(--success-icon)' }}>
              0 Days
            </span>
            <p style={{ fontSize: '0.8125rem', color: 'var(--slate-500)', marginTop: '4px' }}>
              Practice questions daily to maintain your study streak
            </p>
          </div>
        </Card>

        <Card title="Target Curriculum" subtitle="Placement role profile">
          <div style={{ padding: '16px 0' }}>
            <span style={{ fontSize: '1.125rem', fontWeight: 600, color: 'var(--slate-800)' }}>
              {profile?.target_role || 'Junior Python Developer'}
            </span>
            <p style={{ fontSize: '0.8125rem', color: 'var(--slate-500)', marginTop: '6px' }}>
              Curriculum dynamically prioritizes role competencies and core domains.
            </p>
          </div>
        </Card>
      </div>
    </div>
  );
};
