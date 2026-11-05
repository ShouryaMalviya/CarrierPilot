import React from 'react';
import { Card } from '../components/common/Card';
import { EthicalDisclaimerBanner } from '../components/common/EthicalDisclaimerBanner';

export const PracticePage: React.FC = () => {
  return (
    <div>
      <EthicalDisclaimerBanner />
      <div style={{ marginBottom: '24px' }}>
        <h2 style={{ fontSize: '1.5rem', fontWeight: 700, color: 'var(--slate-900)' }}>
          Diagnostic Practice Room
        </h2>
        <p style={{ color: 'var(--slate-500)', fontSize: '0.875rem' }}>
          Interactive MCQ question bank, adaptive next-question recommendations, and real-time mastery tracking.
        </p>
      </div>

      <Card title="Practice Sessions" subtitle="Active diagnostic quizzes and topic taxonomy">
        <div style={{ padding: '32px 0', textAlign: 'center', color: 'var(--slate-500)' }}>
          <p>Diagnostic practice questions workspace.</p>
        </div>
      </Card>
    </div>
  );
};
