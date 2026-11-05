import React from 'react';
import { ShieldCheck } from 'lucide-react';

interface EthicalDisclaimerProps {
  customMessage?: string;
  className?: string;
}

export const EthicalDisclaimerBanner: React.FC<EthicalDisclaimerProps> = ({
  customMessage,
  className = '',
}) => {
  const message =
    customMessage ||
    'CareerPilot AI provides automated content relevance scores and coaching guidance. It does not predict interview callbacks or hiring outcomes, nor guarantee placement. The platform does not infer personality, honesty, or biometric states from voice or appearance.';

  return (
    <div
      className={`alert alert-info ${className}`}
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: '12px',
        fontSize: '0.8125rem',
        lineHeight: 1.4,
        marginBottom: '16px',
      }}
      role="note"
      aria-label="Ethical placement intelligence disclosure"
    >
      <ShieldCheck size={20} style={{ flexShrink: 0, color: 'var(--info-icon)' }} />
      <span>{message}</span>
    </div>
  );
};
