import React, { useState } from 'react';
import Navbar from './components/Navbar';
import Generator from './components/Generator';
import JobTracker from './components/JobTracker';
import CertificatePreviewModal from './components/CertificatePreviewModal';
import ApiDocs from './components/ApiDocs';
import Toast from './components/Toast';
import { Award, ExternalLink } from 'lucide-react';
import './App.css';

export default function App() {
  const [activeTab, setActiveTab] = useState('generate'); // 'generate' | 'tracker' | 'preview' | 'docs'
  const [apiBaseUrl, setApiBaseUrl] = useState('http://127.0.0.1:8000');
  const [trackedJobId, setTrackedJobId] = useState('');
  const [previewCert, setPreviewCert] = useState(null);
  const [toasts, setToasts] = useState([]);

  const addToast = ({ type = 'info', title, message }) => {
    const id = Date.now() + Math.random().toString(36).substring(2, 6);
    const newToast = { id, type, title, message };
    setToasts((prev) => [...prev, newToast]);

    setTimeout(() => {
      removeToast(id);
    }, 4500);
  };

  const removeToast = (id) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  };

  const handleJobSubmitted = (newJobId) => {
    setTrackedJobId(newJobId);
    setActiveTab('tracker');
    addToast({
      type: 'success',
      title: 'Switched to Job Tracker',
      message: `Monitoring progress for job ${newJobId.slice(0, 8)}…`
    });
  };

  const handleDownloadDirect = (certId, recipientName) => {
    if (!trackedJobId) return;
    const downloadUrl = `${apiBaseUrl}/api/v1/jobs/${trackedJobId}/certificates/${certId}/download`;
    const link = document.createElement('a');
    link.href = downloadUrl;
    link.download = `certificate_${recipientName.replace(/\s+/g, '_')}.pdf`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    addToast({ type: 'info', message: `Downloading PDF for ${recipientName}…` });
  };

  return (
    <div className="app-container">
      {/* Navigation Header */}
      <Navbar
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        apiBaseUrl={apiBaseUrl}
        setApiBaseUrl={setApiBaseUrl}
      />

      {/* Main Tab Panels */}
      <main className="main-wrapper" id="main-content">
        {activeTab === 'generate' && (
          <Generator
            apiBaseUrl={apiBaseUrl}
            onJobSubmitted={handleJobSubmitted}
            addToast={addToast}
          />
        )}

        {activeTab === 'tracker' && (
          <JobTracker
            initialJobId={trackedJobId}
            apiBaseUrl={apiBaseUrl}
            addToast={addToast}
            onPreviewCertificate={(cert) => setPreviewCert(cert)}
          />
        )}

        {activeTab === 'preview' && (
          <div className="fade-in">
            <div className="glass-panel" style={{ padding: '1.5rem', marginBottom: '1.5rem', textAlign: 'center' }}>
              <h2 style={{ fontSize: '1.25rem', fontWeight: 700, color: 'var(--text-primary)' }}>
                Template Specification & Layout Inspector
              </h2>
              <p style={{ color: 'var(--text-secondary)', fontSize: '0.8125rem', marginTop: '0.25rem' }}>
                Preview how certificates are formatted with ReportLab canvas graphics, typography hierarchy, and academic seals.
              </p>
            </div>

            <div style={{ maxWidth: '850px', margin: '0 auto' }}>
              <div 
                style={{
                  backgroundColor: '#FDFAF3',
                  color: '#1A2E4A',
                  padding: '3rem 2.5rem',
                  borderRadius: '10px',
                  border: '6px double #C9A84C',
                  boxShadow: 'var(--shadow-md)',
                  position: 'relative',
                  textAlign: 'center',
                  fontFamily: 'serif'
                }}
              >
                <div style={{ borderBottom: '2px solid #C9A84C', paddingBottom: '0.75rem', marginBottom: '1.5rem' }}>
                  <div style={{ fontSize: '0.875rem', letterSpacing: '0.25em', textTransform: 'uppercase', color: '#5A5A5A', fontWeight: 700 }}>
                    AEREO AEROSPACE & ROBOTICS ACADEMY
                  </div>
                  <div style={{ fontSize: '0.75rem', color: '#888888', fontStyle: 'italic', marginTop: '3px' }}>
                    Office of Academic Credentialing & Certification
                  </div>
                </div>

                <div style={{ fontSize: '2rem', letterSpacing: '0.12em', color: '#1A2E4A', textTransform: 'uppercase', margin: '0.75rem 0', fontWeight: 800 }}>
                  Certificate of Achievement
                </div>

                <p style={{ fontSize: '0.875rem', color: '#5A5A5A', fontStyle: 'italic', margin: '1rem 0' }}>
                  This distinction is formally presented to
                </p>

                <div 
                  style={{ 
                    fontSize: '2.25rem', 
                    color: '#1A2E4A', 
                    fontWeight: 700, 
                    borderBottom: '2.5px solid #C9A84C', 
                    display: 'inline-block',
                    padding: '0 2.5rem 0.35rem 2.5rem',
                    margin: '0.5rem auto 1.25rem auto'
                  }}
                >
                  Alexander Wright
                </div>

                <p style={{ fontSize: '0.875rem', color: '#5A5A5A', maxWidth: '580px', margin: '0 auto 0.75rem auto' }}>
                  in recognition of successful completion and outstanding performance in the advanced curriculum of
                </p>

                <div style={{ fontSize: '1.35rem', color: '#C9A84C', fontWeight: 700, margin: '0.5rem 0 1.5rem 0' }}>
                  Autonomous UAV Navigation & Computer Vision Point Clouds
                </div>

                <div style={{ fontSize: '0.8125rem', color: '#5A5A5A', marginBottom: '2.5rem' }}>
                  Issued at: <strong>Annual Geospatial & Autonomous Systems Fellowship 2024</strong>
                </div>

                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end', marginTop: '2.5rem', paddingTop: '1.25rem', borderTop: '1px solid #E5DFD3' }}>
                  <div style={{ textAlign: 'left' }}>
                    <div style={{ fontSize: '0.8125rem', color: '#1A2E4A', fontWeight: 700 }}>
                      Date: 2024-11-15
                    </div>
                    <div style={{ fontSize: '0.7rem', color: '#888888', fontFamily: 'var(--font-mono)' }}>
                      Verification ID: 3fa85f64-5717-4562-b3fc
                    </div>
                  </div>

                  <div 
                    style={{ 
                      width: '64px', 
                      height: '64px', 
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
                    <Award size={32} />
                  </div>

                  <div style={{ textAlign: 'right' }}>
                    <div style={{ fontFamily: 'cursive', fontSize: '1.25rem', color: '#1A2E4A' }}>
                      Aereo Academy Board
                    </div>
                    <div style={{ fontSize: '0.75rem', color: '#5A5A5A', borderTop: '1px solid #888888', paddingTop: '2px' }}>
                      Authorized Program Director
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}

        {activeTab === 'docs' && (
          <ApiDocs apiBaseUrl={apiBaseUrl} addToast={addToast} />
        )}
      </main>

      {/* Clean Footer */}
      <footer 
        style={{ 
          borderTop: '1px solid var(--border-default)', 
          backgroundColor: 'var(--bg-subtle)', 
          padding: '1.75rem 1.5rem', 
          marginTop: 'auto' 
        }}
        role="contentinfo"
      >
        <div 
          style={{ 
            maxWidth: '1200px', 
            margin: '0 auto', 
            display: 'flex', 
            justifyContent: 'space-between', 
            alignItems: 'center', 
            flexWrap: 'wrap', 
            gap: '1rem' 
          }}
        >
          <div>
            <div style={{ fontWeight: 700, fontSize: '0.9375rem', color: 'var(--text-primary)' }}>
              Cert<span style={{ color: 'var(--text-muted)' }}>Forge</span>
            </div>
            <p style={{ color: 'var(--text-muted)', fontSize: '0.75rem', marginTop: '0.125rem' }}>
              Bulk PDF Certificate Generator • Built with FastAPI, SQLite, ReportLab & React
            </p>
          </div>

          <div style={{ display: 'flex', gap: '1.25rem', alignItems: 'center' }}>
            <a
              href={`${apiBaseUrl}/docs`}
              target="_blank"
              rel="noreferrer"
              style={{ color: 'var(--text-secondary)', fontSize: '0.8125rem', textDecoration: 'none', display: 'flex', alignItems: 'center', gap: '0.25rem' }}
            >
              <span>Swagger API Docs</span>
              <ExternalLink size={12} aria-hidden="true" />
            </a>
            <a
              href={`${apiBaseUrl}/health`}
              target="_blank"
              rel="noreferrer"
              style={{ color: 'var(--text-secondary)', fontSize: '0.8125rem', textDecoration: 'none', display: 'flex', alignItems: 'center', gap: '0.25rem' }}
            >
              <span>API Health</span>
              <ExternalLink size={12} aria-hidden="true" />
            </a>
          </div>
        </div>
      </footer>

      {/* Certificate Preview Modal */}
      {previewCert && (
        <CertificatePreviewModal
          cert={previewCert}
          onClose={() => setPreviewCert(null)}
          onDownload={handleDownloadDirect}
        />
      )}

      {/* Toast Alert Notifications */}
      <Toast toasts={toasts} removeToast={removeToast} />
    </div>
  );
}
