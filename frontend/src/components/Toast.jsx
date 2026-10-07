import React from 'react';
import { CheckCircle2, AlertCircle, Info, X } from 'lucide-react';

export default function Toast({ toasts, removeToast }) {
  if (!toasts || toasts.length === 0) return null;

  return (
    <div 
      className="toast-container" 
      role="region" 
      aria-label="Notifications"
    >
      {toasts.map((t) => (
        <div 
          key={t.id} 
          className="toast"
          role="status"
          aria-live="polite"
        >
          {t.type === 'success' && <CheckCircle2 size={16} color="#166534" aria-hidden="true" />}
          {t.type === 'error' && <AlertCircle size={16} color="#991b1b" aria-hidden="true" />}
          {t.type === 'info' && <Info size={16} color="#09090b" aria-hidden="true" />}
          
          <div style={{ flex: 1, minWidth: 0 }}>
            {t.title && (
              <div style={{ fontWeight: 600, fontSize: '0.8125rem', color: 'var(--text-primary)', marginBottom: '0.125rem' }}>
                {t.title}
              </div>
            )}
            <div style={{ color: 'var(--text-secondary)', fontSize: '0.75rem', lineHeight: 1.4, wordBreak: 'break-word' }}>
              {t.message}
            </div>
          </div>

          <button
            type="button"
            onClick={() => removeToast(t.id)}
            aria-label="Dismiss notification"
            style={{
              background: 'none',
              border: 'none',
              color: 'var(--text-muted)',
              cursor: 'pointer',
              padding: '2px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              borderRadius: 'var(--radius-xs)'
            }}
          >
            <X size={14} aria-hidden="true" />
          </button>
        </div>
      ))}
    </div>
  );
}
