import React from 'react';
import { Card } from '../components/common/Card';
import { EthicalDisclaimerBanner } from '../components/common/EthicalDisclaimerBanner';

export const InterviewsPage: React.FC = () => {
  return (
    <div>
      <EthicalDisclaimerBanner />
      <div style={{ marginBottom: '24px' }}>
        <h2 style={{ fontSize: '1.5rem', fontWeight: 700, color: 'var(--slate-900)' }}>
          Mock Interview Studio
        </h2>
        <p style={{ color: 'var(--slate-500)', fontSize: '0.875rem' }}>
          Typed-first technical and behavioral interview sessions evaluated against the 5-dimension coaching rubric.
        </p>
      </div>

      <Card title="Interview Sessions" subtitle="Curated prompts and rubric feedback">
        <div style={{ padding: '32px 0', textAlign: 'center', color: 'var(--slate-500)' }}>
          <p>Mock interview studio and rubric coaching workspace.</p>
        </div>
      </Card>
    </div>
  );
};

