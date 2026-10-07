import React, { useEffect } from 'react';
import { X, Award, Download } from 'lucide-react';

export default function CertificatePreviewModal({ cert, onClose, onDownload }) {
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [onClose]);

  if (!cert) return null;

  return (
    <div 
      className="modal-overlay" 
      onClick={onClose}
      role="dialog"
      aria-modal="true"
      aria-labelledby="preview-modal-title"
    >
      <div 
        className="modal-content fade-in" 
        onClick={(e) => e.stopPropagation()}
      >
        {/* Modal Topbar */}
        <div 
          style={{ 
            display: 'flex', 
            alignItems: 'center', 
            justifyContent: 'space-between', 
            padding: '1rem 1.5rem', 
            borderBottom: '1px solid var(--border-default)' 
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <Award size={18} aria-hidden="true" />
            <h3 id="preview-modal-title" style={{ fontSize: '1rem', fontWeight: 600, color: 'var(--text-primary)' }}>
              Certificate Template Preview
            </h3>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            {cert.status === 'success' && onDownload && (
              <button
                type="button"
                className="btn btn-primary btn-sm"
                onClick={() => onDownload(cert.id, cert.recipient_name)}
              >
                <Download size={13} aria-hidden="true" /> Download PDF
              </button>
            )}
            <button
              type="button"
              onClick={onClose}
              aria-label="Close dialog"
              className="btn btn-outline btn-sm"
              style={{ padding: '0.375rem' }}
            >
              <X size={16} aria-hidden="true" />
            </button>
          </div>
        </div>

        {/* Certificate Mock Canvas based on ReportLab layout */}
        <div style={{ padding: '1.5rem', backgroundColor: 'var(--bg-muted)' }}>
          <div 
            style={{
              backgroundColor: '#FDFAF3',
              color: '#1A2E4A',
              padding: '2.5rem 2rem',
              borderRadius: '8px',
              border: '6px double #C9A84C',
              boxShadow: 'var(--shadow-md)',
              position: 'relative',
              textAlign: 'center',
              fontFamily: 'serif',
              overflow: 'hidden'
            }}
          >
            {/* Background Watermark Seal */}
            <div 
              style={{
                position: 'absolute',
                top: '50%',
                left: '50%',
                transform: 'translate(-50%, -50%)',
                fontSize: '160px',
                opacity: 0.04,
                pointerEvents: 'none',
                userSelect: 'none'
              }}
              aria-hidden="true"
            >
              🎓
            </div>

            {/* Top decorative header band */}
            <div style={{ borderBottom: '2px solid #C9A84C', paddingBottom: '0.75rem', marginBottom: '1.25rem' }}>
              <div style={{ fontSize: '0.8125rem', letterSpacing: '0.2em', textTransform: 'uppercase', color: '#5A5A5A', fontWeight: 600 }}>
                {cert.issuer_name || 'Aereo Aerospace Academy'}
              </div>
              <div style={{ fontSize: '0.75rem', color: '#888888', fontStyle: 'italic', marginTop: '2px' }}>
                Office of Academic Credentials
              </div>
            </div>

            <h1 style={{ fontSize: '1.75rem', letterSpacing: '0.1em', color: '#1A2E4A', textTransform: 'uppercase', margin: '0.5rem 0', fontWeight: 800 }}>
              Certificate of Achievement
            </h1>

            <p style={{ fontSize: '0.875rem', color: '#5A5A5A', fontStyle: 'italic', margin: '0.75rem 0' }}>
              This distinction is formally presented to
            </p>

            {/* Recipient Name in bold display */}
            <div 
              style={{ 
                fontSize: '2rem', 
                color: '#1A2E4A', 
                fontWeight: 700, 
                borderBottom: '2px solid #C9A84C', 
                display: 'inline-block',
                padding: '0 2rem 0.25rem 2rem',
                margin: '0.5rem auto 1rem auto'
              }}
            >
              {cert.recipient_name || 'Jane Doe'}
            </div>

            <p style={{ fontSize: '0.875rem', color: '#5A5A5A', maxWidth: '500px', margin: '0 auto 0.5rem auto' }}>
              in recognition of outstanding completion and excellence in the curriculum of
            </p>

            <h2 style={{ fontSize: '1.25rem', color: '#C9A84C', fontWeight: 700, margin: '0.5rem 0 1.25rem 0' }}>
              {cert.course_name || 'Autonomous UAV Navigation & Mapping'}
            </h2>

            <div style={{ fontSize: '0.8125rem', color: '#5A5A5A', marginBottom: '2rem' }}>
              Organized under: <strong>{cert.event_name || 'Aereo Tech Summit 2024'}</strong>
            </div>

            {/* Signatures & Seal Footer */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end', marginTop: '2rem', paddingTop: '1rem', borderTop: '1px solid #E5DFD3' }}>
              <div style={{ textAlign: 'left' }}>
                <div style={{ fontSize: '0.8125rem', color: '#1A2E4A', fontWeight: 700 }}>
                  Date: {cert.issue_date || '2024-11-15'}
                </div>
                <div style={{ fontSize: '0.6875rem', color: '#888888', fontFamily: 'var(--font-mono)' }}>
                  ID: {cert.id ? cert.id.slice(0, 16) : 'VERIF-SAMPLE-99'}
                </div>
              </div>

              {/* Seal Graphic */}
              <div 
                style={{ 
                  width: '56px', 
                  height: '56px', 
                  borderRadius: '50%', 
                  backgroundColor: '#F5E6C0',
                  border: '2px solid #C9A84C',
                  display: 'flex', 
                  alignItems: 'center', 
                  justifyContent: 'center', 
                  color: '#1A2E4A'
                }}
                aria-hidden="true"
              >
                <Award size={26} />
              </div>

              <div style={{ textAlign: 'right' }}>
                <div style={{ fontFamily: 'cursive', fontSize: '1.15rem', color: '#1A2E4A' }}>
                  {cert.issuer_name || 'Authorized Signatory'}
                </div>
                <div style={{ fontSize: '0.75rem', color: '#5A5A5A', borderTop: '1px solid #888888', paddingTop: '2px' }}>
                  Authorized Signatory
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Modal Footer */}
        <div 
          style={{ 
            padding: '0.875rem 1.5rem', 
            backgroundColor: 'var(--bg-subtle)', 
            borderTop: '1px solid var(--border-default)',
            display: 'flex', 
            justifyContent: 'space-between', 
            alignItems: 'center' 
          }}
        >
          <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
            Rendered with ReportLab vector graphics matching backend specifications.
          </span>
          <button type="button" className="btn btn-outline btn-sm" onClick={onClose}>
            Close Preview
          </button>
        </div>
      </div>
    </div>
  );
}
