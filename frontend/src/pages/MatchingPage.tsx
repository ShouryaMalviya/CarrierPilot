import React from 'react';
import { Card } from '../components/common/Card';
import { EthicalDisclaimerBanner } from '../components/common/EthicalDisclaimerBanner';

export const MatchingPage: React.FC = () => {
  return (
    <div>
      <EthicalDisclaimerBanner />
      <div style={{ marginBottom: '24px' }}>
        <h2 style={{ fontSize: '1.5rem', fontWeight: 700, color: 'var(--slate-900)' }}>
          Job Description Matching & Skill Gap Analysis
        </h2>
        <p style={{ color: 'var(--slate-500)', fontSize: '0.875rem' }}>
          Hybrid explainable ranking with required skill coverage, semantic relevance, and missing skill remediation.
        </p>
      </div>

      <Card title="Job Postings" subtitle="Live and synthetic opportunities">
        <div style={{ padding: '32px 0', textAlign: 'center', color: 'var(--slate-500)' }}>
          <p>Job matching workspace and ranking diagnostics.</p>
        </div>
      </Card>
    </div>
  );
};

