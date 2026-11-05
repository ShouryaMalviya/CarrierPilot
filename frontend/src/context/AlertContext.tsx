import React, { createContext, useContext, useState } from 'react';

export type AlertType = 'success' | 'warning' | 'danger' | 'info';

export interface AlertMessage {
  id: string;
  type: AlertType;
  message: string;
}

interface AlertContextType {
  alerts: AlertMessage[];
  showAlert: (message: string, type?: AlertType, autoDismissMs?: number) => void;
  removeAlert: (id: string) => void;
  clearAlerts: () => void;
}

const AlertContext = createContext<AlertContextType | undefined>(undefined);

export const AlertProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [alerts, setAlerts] = useState<AlertMessage[]>([]);

  const showAlert = (message: string, type: AlertType = 'info', autoDismissMs: number = 5000) => {
    const id = Math.random().toString(36).substring(2, 9);
    const newAlert: AlertMessage = { id, type, message };

    setAlerts((prev) => [...prev, newAlert]);

    if (autoDismissMs > 0) {
      setTimeout(() => {
        removeAlert(id);
      }, autoDismissMs);
    }
  };

  const removeAlert = (id: string) => {
    setAlerts((prev) => prev.filter((a) => a.id !== id));
  };

  const clearAlerts = () => {
    setAlerts([]);
  };

  return (
    <AlertContext.Provider value={{ alerts, showAlert, removeAlert, clearAlerts }}>
      {children}
      {/* Toast Render Viewport */}
      {alerts.length > 0 && (
        <div
          style={{
            position: 'fixed',
            top: '20px',
            right: '20px',
            zIndex: 9999,
            display: 'flex',
            flexDirection: 'column',
            gap: '8px',
            maxWidth: '420px',
          }}
        >
          {alerts.map((alert) => (
            <div
              key={alert.id}
              className={`alert alert-${alert.type}`}
              style={{
                boxShadow: 'var(--shadow-lg)',
                margin: 0,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
              }}
              role="alert"
            >
              <span>{alert.message}</span>
              <button
                onClick={() => removeAlert(alert.id)}
                style={{
                  background: 'none',
                  border: 'none',
                  cursor: 'pointer',
                  padding: '2px 6px',
                  fontWeight: 'bold',
                  color: 'inherit',
                }}
                aria-label="Close"
              >
                ×
              </button>
            </div>
          ))}
        </div>
      )}
    </AlertContext.Provider>
  );
};

export const useAlert = () => {
  const context = useContext(AlertContext);
  if (!context) {
    throw new Error('useAlert must be used within an AlertProvider');
  }
  return context;
};

