import React from 'react';
import { Card } from '../components/common/Card';
import { EthicalDisclaimerBanner } from '../components/common/EthicalDisclaimerBanner';

export const ProgressPage: React.FC = () => {
  return (
    <div>
      <EthicalDisclaimerBanner />
      <div style={{ marginBottom: '24px' }}>
        <h2 style={{ fontSize: '1.5rem', fontWeight: 700, color: 'var(--slate-900)' }}>
          Learner Progress & Evaluation Auditing
        </h2>
        <p style={{ color: 'var(--slate-500)', fontSize: '0.875rem' }}>
          Topic mastery analytics, attempt histories, coaching fairness audits, and telemetry reporting.
        </p>
      </div>

      <Card title="Progress Telemetry" subtitle="Topic mastery trends and evaluation logs">
        <div style={{ padding: '32px 0', textAlign: 'center', color: 'var(--slate-500)' }}>
          <p>Progress and telemetry analytics dashboard.</p>
        </div>
      </Card>
    </div>
  );
};
