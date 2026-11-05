import React from 'react';
import { Link } from 'react-router-dom';
import { Compass } from 'lucide-react';

export const NotFoundPage: React.FC = () => {
  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        minHeight: '60vh',
        textAlign: 'center',
        padding: '32px',
      }}
    >
      <Compass size={64} style={{ color: 'var(--primary-600)', marginBottom: '16px' }} />
      <h2 style={{ fontSize: '2rem', fontWeight: 700, color: 'var(--slate-900)' }}>
        404 - Page Not Found
      </h2>
      <p style={{ color: 'var(--slate-500)', maxWidth: '420px', margin: '8px auto 24px' }}>
        The navigation coordinates you requested do not exist in CareerPilot AI.
      </p>
      <Link to="/dashboard" className="btn btn-primary">
        Return to Dashboard
      </Link>
    </div>
  );
};

