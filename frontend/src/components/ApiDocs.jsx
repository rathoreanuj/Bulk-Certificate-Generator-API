import React, { useState } from 'react';
import { ExternalLink, Copy, Check, BookOpen } from 'lucide-react';

const ENDPOINTS = [
  {
    method: 'POST',
    path: '/api/v1/jobs',
    title: 'Submit Bulk Generation Job',
    desc: 'Accepts an event specification and a list of recipients. Enqueues background generation task and immediately returns HTTP 202 Accepted with a job_id.',
    sampleBody: `{
  "event_name": "TechConf 2024",
  "issuer_name": "Aereo Academy",
  "issue_date": "2024-11-15",
  "recipients": [
    {
      "recipient_name": "Alice Johnson",
      "recipient_email": "alice@example.com",
      "course_name": "Advanced Python Programming"
    }
  ]
}`,
    curl: `curl -X POST http://127.0.0.1:8000/api/v1/jobs \\
  -H "Content-Type: application/json" \\
  -d '{
    "event_name": "TechConf 2024",
    "issuer_name": "Aereo Academy",
    "issue_date": "2024-11-15",
    "recipients": [
      {"recipient_name": "Alice Johnson", "recipient_email": "alice@example.com", "course_name": "Advanced Python"}
    ]
  }'`
  },
  {
    method: 'GET',
    path: '/api/v1/jobs/{job_id}',
    title: 'Poll Job Status & Counters',
    desc: 'Retrieves current status (pending, processing, completed, failed) along with total, success, pending, and failed counts.',
    curl: `curl http://127.0.0.1:8000/api/v1/jobs/{job_id}`
  },
  {
    method: 'GET',
    path: '/api/v1/jobs/{job_id}/certificates',
    title: 'List All Certificates in Job',
    desc: 'Returns an array of individual certificate records including recipient metadata, status (pending, success, failed), and error messages if any.',
    curl: `curl http://127.0.0.1:8000/api/v1/jobs/{job_id}/certificates`
  },
  {
    method: 'GET',
    path: '/api/v1/jobs/{job_id}/certificates/{id}/download',
    title: 'Download Generated PDF',
    desc: 'Streams the ReportLab generated PDF file. Returns HTTP 409 Conflict if certificate is not completed yet.',
    curl: `curl -O -J http://127.0.0.1:8000/api/v1/jobs/{job_id}/certificates/{certificate_id}/download`
  },
  {
    method: 'GET',
    path: '/api/v1/jobs/{job_id}/download-zip',
    title: 'Download All Completed Certificates (.ZIP)',
    desc: 'Streams an in-memory compressed ZIP archive containing all successfully generated certificate PDFs for the job.',
    curl: `curl -O -J http://127.0.0.1:8000/api/v1/jobs/{job_id}/download-zip`
  },
  {
    method: 'POST',
    path: '/api/v1/jobs/{job_id}/retry',
    title: 'Retry Failed Certificates in Job',
    desc: 'Finds all failed records within the job, resets their status to pending, and re-enqueues background workers.',
    curl: `curl -X POST http://127.0.0.1:8000/api/v1/jobs/{job_id}/retry`
  },
  {
    method: 'GET',
    path: '/api/v1/verify/{certificate_id}',
    title: 'Public Certificate Verification Registry',
    desc: 'Public unauthenticated endpoint to verify authenticity, recipient name, course, issuer, and issue date for any issued certificate.',
    curl: `curl http://127.0.0.1:8000/api/v1/verify/{certificate_id}`
  },
  {
    method: 'GET',
    path: '/health',
    title: 'Service Health Check',
    desc: 'Returns {"status": "ok", "service": "bulk-certificate-generator"} when service is active.',
    curl: `curl http://127.0.0.1:8000/health`
  }
];

export default function ApiDocs({ apiBaseUrl, addToast }) {
  const [copiedIdx, setCopiedIdx] = useState(null);

  const copyToClipboard = (text, idx) => {
    navigator.clipboard.writeText(text);
    setCopiedIdx(idx);
    addToast({ type: 'info', message: 'cURL command copied to clipboard!' });
    setTimeout(() => setCopiedIdx(null), 2000);
  };

  return (
    <div className="fade-in">
      {/* Header Panel */}
      <div className="glass-panel" style={{ padding: '1.5rem', marginBottom: '1.5rem' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '1rem' }}>
          <div>
            <h2 style={{ fontSize: '1.25rem', fontWeight: 700, color: 'var(--text-primary)', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <BookOpen size={20} aria-hidden="true" />
              REST API & Architecture Reference
            </h2>
            <p style={{ color: 'var(--text-secondary)', fontSize: '0.8125rem', marginTop: '0.25rem' }}>
              Built with FastAPI, Pydantic v2, SQLite/SQLAlchemy, and ReportLab canvas engine.
            </p>
          </div>

          <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
            <a
              href={`${apiBaseUrl || 'http://127.0.0.1:8000'}/docs`}
              target="_blank"
              rel="noreferrer"
              className="btn btn-primary btn-sm"
            >
              <ExternalLink size={13} aria-hidden="true" />
              Interactive Swagger (/docs)
            </a>
            <a
              href={`${apiBaseUrl || 'http://127.0.0.1:8000'}/redoc`}
              target="_blank"
              rel="noreferrer"
              className="btn btn-outline btn-sm"
            >
              <ExternalLink size={13} aria-hidden="true" />
              ReDoc (/redoc)
            </a>
          </div>
        </div>
      </div>

      {/* Endpoints List */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr', gap: '1rem' }}>
        {ENDPOINTS.map((ep, idx) => (
          <div key={idx} className="glass-panel" style={{ padding: '1.5rem' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '0.75rem', marginBottom: '0.75rem' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.625rem' }}>
                <span
                  style={{
                    padding: '0.2rem 0.5rem',
                    borderRadius: 'var(--radius-xs)',
                    fontFamily: 'var(--font-mono)',
                    fontSize: '0.6875rem',
                    fontWeight: 700,
                    backgroundColor: ep.method === 'POST' ? '#09090b' : 'var(--bg-muted)',
                    color: ep.method === 'POST' ? '#ffffff' : 'var(--text-primary)',
                    border: '1px solid var(--border-default)',
                    lineHeight: 1
                  }}
                >
                  {ep.method}
                </span>
                <code style={{ fontFamily: 'var(--font-mono)', fontSize: '0.875rem', color: 'var(--text-primary)', fontWeight: 600 }}>
                  {ep.path}
                </code>
              </div>

              <button
                type="button"
                className="btn btn-outline btn-sm"
                onClick={() => copyToClipboard(ep.curl, idx)}
                aria-label={`Copy cURL command for ${ep.title}`}
              >
                {copiedIdx === idx ? <Check size={13} aria-hidden="true" /> : <Copy size={13} aria-hidden="true" />}
                <span>{copiedIdx === idx ? 'Copied' : 'Copy cURL'}</span>
              </button>
            </div>

            <h3 style={{ fontSize: '0.9375rem', fontWeight: 600, color: 'var(--text-primary)', marginBottom: '0.25rem' }}>
              {ep.title}
            </h3>
            <p style={{ fontSize: '0.8125rem', color: 'var(--text-secondary)', marginBottom: '1rem' }}>
              {ep.desc}
            </p>

            {ep.sampleBody && (
              <div style={{ marginBottom: '1rem' }}>
                <div style={{ fontSize: '0.6875rem', color: 'var(--text-muted)', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.04em', marginBottom: '0.375rem' }}>
                  Request Payload Schema
                </div>
                <pre
                  style={{
                    backgroundColor: 'var(--bg-subtle)',
                    padding: '0.875rem 1rem',
                    borderRadius: 'var(--radius-sm)',
                    fontSize: '0.75rem',
                    fontFamily: 'var(--font-mono)',
                    color: 'var(--text-primary)',
                    overflowX: 'auto',
                    border: '1px solid var(--border-default)'
                  }}
                >
                  {ep.sampleBody}
                </pre>
              </div>
            )}

            <div>
              <div style={{ fontSize: '0.6875rem', color: 'var(--text-muted)', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.04em', marginBottom: '0.375rem' }}>
                cURL Request Example
              </div>
              <pre
                style={{
                  backgroundColor: 'var(--bg-subtle)',
                  padding: '0.75rem 1rem',
                  borderRadius: 'var(--radius-sm)',
                  fontSize: '0.75rem',
                  fontFamily: 'var(--font-mono)',
                  color: 'var(--text-primary)',
                  overflowX: 'auto',
                  border: '1px solid var(--border-default)'
                }}
              >
                {ep.curl}
              </pre>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
