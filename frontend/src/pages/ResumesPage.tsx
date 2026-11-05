import React from 'react';
import { Card } from '../components/common/Card';
import { EthicalDisclaimerBanner } from '../components/common/EthicalDisclaimerBanner';

export const ResumesPage: React.FC = () => {
  return (
    <div>
      <EthicalDisclaimerBanner />
      <div style={{ marginBottom: '24px' }}>
        <h2 style={{ fontSize: '1.5rem', fontWeight: 700, color: 'var(--slate-900)' }}>
          Resume Workspace
        </h2>
        <p style={{ color: 'var(--slate-500)', fontSize: '0.875rem' }}>
          Upload PDF/DOCX resumes, extract technical skills, and manage evidence snippets.
        </p>
      </div>

      <Card title="Uploaded Resumes" subtitle="Document intake and skill taxonomy extraction">
        <div style={{ padding: '32px 0', textAlign: 'center', color: 'var(--slate-500)' }}>
          <p>Resume management and parsing workspace.</p>
        </div>
      </Card>
    </div>
  );
};

