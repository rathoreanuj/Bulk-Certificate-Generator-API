import React, { useState, useEffect, useRef } from 'react';
import { 
  Search, 
  RefreshCw, 
  Download, 
  CheckCircle2, 
  Clock, 
  XCircle, 
  Eye, 
  Copy, 
  Layers, 
  Calendar, 
  Building,
  Check,
  Archive,
  RotateCcw
} from 'lucide-react';

export default function JobTracker({ 
  initialJobId, 
  apiBaseUrl, 
  addToast, 
  onPreviewCertificate 
}) {
  const [jobId, setJobId] = useState(initialJobId || '');
  const [jobData, setJobData] = useState(null);
  const [certificates, setCertificates] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [autoPoll, setAutoPoll] = useState(true);
  const [filterStatus, setFilterStatus] = useState('all'); // 'all' | 'success' | 'pending' | 'failed'
  const [searchQuery, setSearchQuery] = useState('');
  const [recentJobs, setRecentJobs] = useState([]);

  const pollIntervalRef = useRef(null);

  // Sync initialJobId if passed from Generator
  useEffect(() => {
    if (initialJobId && initialJobId !== jobId) {
      setJobId(initialJobId);
      fetchJobDetails(initialJobId);
    }
  }, [initialJobId]);

  // Load recent jobs from localStorage
  useEffect(() => {
    try {
      const stored = localStorage.getItem('certforge_recent_jobs');
      if (stored) {
        setRecentJobs(JSON.parse(stored));
      }
    } catch {
      // Ignore
    }
  }, []);

  const saveToRecentJobs = (id, eventName) => {
    try {
      let list = recentJobs.filter(j => j.id !== id);
      list.unshift({ id, eventName: eventName || 'Certificate Job', timestamp: new Date().toISOString() });
      if (list.length > 8) list = list.slice(0, 8);
      setRecentJobs(list);
      localStorage.setItem('certforge_recent_jobs', JSON.stringify(list));
    } catch {
      // Ignore
    }
  };

  const fetchJobDetails = async (idToFetch, showLoader = false) => {
    const id = idToFetch || jobId;
    if (!id || !id.trim()) {
      addToast({ type: 'error', message: 'Please enter a valid Job ID.' });
      return;
    }

    if (showLoader) setIsLoading(true);

    try {
      // 1. Fetch Job Status
      const statusRes = await fetch(`${apiBaseUrl}/api/v1/jobs/${id.trim()}`);
      if (!statusRes.ok) {
        if (statusRes.status === 404) {
          throw new Error(`Job '${id}' not found.`);
        }
        throw new Error(`Failed to fetch job (${statusRes.status})`);
      }
      const statusData = await statusRes.json();
      setJobData(statusData);
      saveToRecentJobs(statusData.id, statusData.event_name);

      // 2. Fetch Certificates list
      const certsRes = await fetch(`${apiBaseUrl}/api/v1/jobs/${id.trim()}/certificates`);
      if (certsRes.ok) {
        const certsData = await certsRes.json();
        setCertificates(certsData);
      }

    } catch (err) {
      addToast({ type: 'error', message: err.message });
      setJobData(null);
      setCertificates([]);
    } finally {
      if (showLoader) setIsLoading(false);
    }
  };

  // Auto-polling setup
  useEffect(() => {
    if (pollIntervalRef.current) clearInterval(pollIntervalRef.current);

    if (autoPoll && jobId && jobData?.status !== 'completed' && jobData?.status !== 'failed') {
      pollIntervalRef.current = setInterval(() => {
        fetchJobDetails(jobId, false);
      }, 2500);
    }

    return () => {
      if (pollIntervalRef.current) clearInterval(pollIntervalRef.current);
    };
  }, [autoPoll, jobId, jobData?.status]);

  const handleDownload = (certId, recipientName) => {
    const downloadUrl = `${apiBaseUrl}/api/v1/jobs/${jobData.id}/certificates/${certId}/download`;
    const link = document.createElement('a');
    link.href = downloadUrl;
    link.download = `certificate_${recipientName.replace(/\s+/g, '_')}.pdf`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    addToast({ type: 'info', message: `Downloading certificate for ${recipientName}…` });
  };

  const handleDownloadAll = () => {
    const successes = certificates.filter(c => c.status === 'success');
    if (successes.length === 0) {
      addToast({ type: 'error', message: 'No completed certificates ready for download yet.' });
      return;
    }

    addToast({ type: 'info', message: `Triggering download for ${successes.length} certificates…` });
    successes.forEach((c, idx) => {
      setTimeout(() => {
        handleDownload(c.id, c.recipient_name);
      }, idx * 400);
    });
  };

  const handleDownloadZip = () => {
    if (!jobData || jobData.success_count === 0) {
      addToast({ type: 'error', message: 'No completed certificates available to package into ZIP yet.' });
      return;
    }
    const downloadUrl = `${apiBaseUrl}/api/v1/jobs/${jobData.id}/download-zip`;
    const link = document.createElement('a');
    link.href = downloadUrl;
    link.download = `certificates_${jobData.id.slice(0, 8)}.zip`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    addToast({ type: 'info', message: `Downloading bulk ZIP archive (${jobData.success_count} PDFs)…` });
  };

  const handleRetryFailed = async () => {
    if (!jobData || jobData.failed_count === 0) {
      addToast({ type: 'info', message: 'No failed certificates to retry.' });
      return;
    }
    try {
      const res = await fetch(`${apiBaseUrl}/api/v1/jobs/${jobData.id}/retry`, { method: 'POST' });
      if (!res.ok) throw new Error('Failed to queue retry');
      const data = await res.json();
      addToast({ type: 'success', title: 'Retry Dispatched', message: data.message });
      fetchJobDetails(jobData.id, false);
    } catch (err) {
      addToast({ type: 'error', message: err.message });
    }
  };

  // Filtering
  const filteredCertificates = certificates.filter((c) => {
    const matchesFilter = filterStatus === 'all' || c.status === filterStatus;
    const matchesSearch = 
      c.recipient_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      c.recipient_email.toLowerCase().includes(searchQuery.toLowerCase()) ||
      c.course_name.toLowerCase().includes(searchQuery.toLowerCase());
    return matchesFilter && matchesSearch;
  });

  // Calculate percentage
  const total = jobData ? jobData.total_count : 0;
  const finished = jobData ? (jobData.success_count + jobData.failed_count) : 0;
  const progressPct = total > 0 ? Math.round((finished / total) * 100) : 0;

  return (
    <div className="fade-in">
      {/* Top Search & Controls Panel */}
      <div className="glass-panel" style={{ padding: '1.25rem 1.5rem', marginBottom: '1.5rem' }}>
        <div className="tracker-topbar" style={{ marginBottom: recentJobs.length > 0 ? '0.875rem' : 0 }}>
          <div className="search-job-input-wrapper">
            <Search size={16} aria-hidden="true" />
            <input
              type="text"
              className="form-input"
              placeholder="Paste Job UUID (e.g. eb3d964e-597a-437b-b5c8-033328c5f13f)…"
              value={jobId}
              onChange={(e) => setJobId(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter') fetchJobDetails(jobId, true);
              }}
              aria-label="Job UUID query"
            />
          </div>

          <button
            type="button"
            className="btn btn-primary"
            onClick={() => fetchJobDetails(jobId, true)}
            disabled={isLoading || !jobId.trim()}
          >
            {isLoading ? <RefreshCw size={14} className="animate-spin" aria-hidden="true" /> : <RefreshCw size={14} aria-hidden="true" />}
            <span>Fetch Job</span>
          </button>

          <label 
            style={{ 
              display: 'flex', 
              alignItems: 'center', 
              gap: '0.4375rem', 
              fontSize: '0.8125rem', 
              color: 'var(--text-secondary)', 
              cursor: 'pointer',
              userSelect: 'none'
            }}
          >
            <input
              type="checkbox"
              checked={autoPoll}
              onChange={(e) => setAutoPoll(e.target.checked)}
              style={{ accentColor: '#09090b', cursor: 'pointer' }}
            />
            Auto-refresh (2.5s)
          </label>
        </div>

        {/* Recent Jobs Pills */}
        {recentJobs.length > 0 && (
          <div 
            style={{ 
              display: 'flex', 
              alignItems: 'center', 
              gap: '0.375rem', 
              flexWrap: 'wrap', 
              paddingTop: '0.625rem', 
              borderTop: '1px solid var(--border-default)' 
            }}
          >
            <span style={{ fontSize: '0.6875rem', color: 'var(--text-muted)', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.04em' }}>
              Recent:
            </span>
            {recentJobs.map((j) => (
              <button
                key={j.id}
                type="button"
                className="btn btn-outline btn-sm"
                style={{ fontSize: '0.6875rem', padding: '0.1875rem 0.5rem', fontWeight: 500 }}
                onClick={() => {
                  setJobId(j.id);
                  fetchJobDetails(j.id, true);
                }}
              >
                {j.eventName} ({j.id.slice(0, 8)}…)
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Main Job Monitor View */}
      {jobData && (
        <div>
          {/* Header Card */}
          <div className="glass-panel" style={{ padding: '1.5rem', marginBottom: '1.5rem' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '1rem', marginBottom: '1.25rem' }}>
              <div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.625rem', marginBottom: '0.25rem' }}>
                  <h2 style={{ fontSize: '1.25rem', fontWeight: 700, color: 'var(--text-primary)' }}>
                    {jobData.event_name}
                  </h2>
                  <span className={`badge badge-${jobData.status}`}>
                    {jobData.status}
                  </span>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.875rem', color: 'var(--text-secondary)', fontSize: '0.8125rem' }}>
                  <span style={{ display: 'flex', alignItems: 'center', gap: '0.375rem' }}>
                    <Building size={13} aria-hidden="true" /> {jobData.issuer_name}
                  </span>
                  <span>•</span>
                  <span style={{ display: 'flex', alignItems: 'center', gap: '0.375rem' }}>
                    <Calendar size={13} aria-hidden="true" /> Issued: {jobData.issue_date}
                  </span>
                </div>
              </div>

              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', flexWrap: 'wrap' }}>
                <button
                  type="button"
                  className="btn btn-outline btn-sm"
                  onClick={() => {
                    navigator.clipboard.writeText(jobData.id);
                    addToast({ type: 'info', message: 'Job UUID copied to clipboard.' });
                  }}
                  aria-label="Copy Job UUID"
                >
                  <Copy size={13} aria-hidden="true" /> Copy UUID
                </button>

                {jobData.failed_count > 0 && (
                  <button
                    type="button"
                    className="btn btn-danger btn-sm"
                    onClick={handleRetryFailed}
                    title="Retry generation for failed certificates"
                  >
                    <RotateCcw size={13} aria-hidden="true" /> Retry Failed ({jobData.failed_count})
                  </button>
                )}

                <button
                  type="button"
                  className="btn btn-outline btn-sm"
                  onClick={handleDownloadZip}
                  disabled={jobData.success_count === 0}
                  title="Download all generated certificates as a single ZIP archive"
                >
                  <Archive size={13} aria-hidden="true" /> Download ZIP
                </button>

                <button
                  type="button"
                  className="btn btn-primary btn-sm"
                  onClick={handleDownloadAll}
                  disabled={jobData.success_count === 0}
                >
                  <Download size={13} aria-hidden="true" /> Download All ({jobData.success_count})
                </button>
              </div>
            </div>

            {/* Metrics Counter Deck */}
            <div className="metrics-deck">
              <div className="metric-card">
                <span className="metric-label">
                  Total Recipients <Layers size={13} aria-hidden="true" />
                </span>
                <span className="metric-val">{jobData.total_count}</span>
              </div>
              <div className="metric-card">
                <span className="metric-label">
                  Generated (Success) <CheckCircle2 size={13} aria-hidden="true" />
                </span>
                <span className="metric-val">{jobData.success_count}</span>
              </div>
              <div className="metric-card">
                <span className="metric-label">
                  In Queue (Pending) <Clock size={13} aria-hidden="true" />
                </span>
                <span className="metric-val">{jobData.pending_count}</span>
              </div>
              <div className="metric-card">
                <span className="metric-label">
                  Failed <XCircle size={13} aria-hidden="true" />
                </span>
                <span className="metric-val">{jobData.failed_count}</span>
              </div>
            </div>

            {/* Progress Bar */}
            <div className="progress-card" style={{ marginBottom: 0 }}>
              <div className="progress-header">
                <span style={{ fontSize: '0.8125rem', fontWeight: 500, color: 'var(--text-secondary)' }}>
                  Generation Progress
                </span>
                <span style={{ fontSize: '0.8125rem', fontWeight: 600, color: 'var(--text-primary)' }}>
                  {progressPct}% ({finished} / {total})
                </span>
              </div>
              <div className="progress-track" role="progressbar" aria-valuenow={progressPct} aria-valuemin={0} aria-valuemax={100}>
                <div
                  className="progress-fill"
                  style={{ width: `${progressPct}%` }}
                />
              </div>
            </div>
          </div>

          {/* Certificates Table */}
          <div className="glass-panel table-card">
            <div className="table-header-toolbar">
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <h3 style={{ fontSize: '0.9375rem', fontWeight: 600, color: 'var(--text-primary)' }}>
                  Certificates List ({filteredCertificates.length})
                </h3>
              </div>

              <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', flexWrap: 'wrap' }}>
                {/* Search recipient */}
                <div style={{ position: 'relative', width: '200px' }}>
                  <Search size={13} style={{ position: 'absolute', left: '0.6875rem', top: '50%', transform: 'translateY(-50%)', color: 'var(--text-dim)', pointerEvents: 'none' }} aria-hidden="true" />
                  <input
                    type="text"
                    className="form-input"
                    placeholder="Search recipient…"
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    style={{ paddingLeft: '2rem', padding: '0.3125rem 0.625rem 0.3125rem 2rem', fontSize: '0.8125rem' }}
                    aria-label="Filter certificates by recipient"
                  />
                </div>

                {/* Status Filter Chips */}
                <div className="table-filter-group" role="radiogroup" aria-label="Filter by status">
                  {['all', 'success', 'pending', 'failed'].map((st) => (
                    <button
                      key={st}
                      type="button"
                      className={`filter-btn ${filterStatus === st ? 'active' : ''}`}
                      onClick={() => setFilterStatus(st)}
                      role="radio"
                      aria-checked={filterStatus === st}
                    >
                      {st.charAt(0).toUpperCase() + st.slice(1)}
                    </button>
                  ))}
                </div>
              </div>
            </div>

            <div style={{ overflowX: 'auto' }}>
              <table className="data-table">
                <thead>
                  <tr>
                    <th scope="col">Recipient</th>
                    <th scope="col">Email</th>
                    <th scope="col">Course / Specialization</th>
                    <th scope="col">Status</th>
                    <th scope="col" style={{ textAlign: 'right' }}>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredCertificates.length === 0 ? (
                    <tr>
                      <td colSpan={5} style={{ textAlign: 'center', padding: '2.5rem', color: 'var(--text-muted)' }}>
                        No certificates matching current criteria.
                      </td>
                    </tr>
                  ) : (
                    filteredCertificates.map((cert) => (
                      <tr key={cert.id}>
                        <td>
                          <div style={{ fontWeight: 600, color: 'var(--text-primary)' }}>
                            {cert.recipient_name}
                          </div>
                          <div style={{ fontSize: '0.6875rem', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
                            ID: {cert.id.slice(0, 8)}…
                          </div>
                        </td>
                        <td style={{ color: 'var(--text-secondary)' }}>
                          {cert.recipient_email}
                        </td>
                        <td style={{ color: 'var(--text-primary)' }}>
                          {cert.course_name}
                        </td>
                        <td>
                          <div>
                            <span className={`badge badge-${cert.status}`}>
                              {cert.status}
                            </span>
                            {cert.error_message && (
                              <div style={{ fontSize: '0.6875rem', color: '#b91c1c', marginTop: '0.25rem' }}>
                                {cert.error_message}
                              </div>
                            )}
                          </div>
                        </td>
                        <td style={{ textAlign: 'right' }}>
                          <div style={{ display: 'inline-flex', gap: '0.375rem' }}>
                            <button
                              type="button"
                              className="btn btn-outline btn-sm"
                              onClick={() => onPreviewCertificate({
                                recipient_name: cert.recipient_name,
                                course_name: cert.course_name,
                                event_name: jobData.event_name,
                                issuer_name: jobData.issuer_name,
                                issue_date: jobData.issue_date,
                                recipient_email: cert.recipient_email,
                                status: cert.status,
                                id: cert.id
                              })}
                              title="Inspect Template Layout"
                              aria-label={`Preview certificate for ${cert.recipient_name}`}
                            >
                              <Eye size={13} aria-hidden="true" />
                              Preview
                            </button>

                            <button
                              type="button"
                              className="btn btn-primary btn-sm"
                              disabled={cert.status !== 'success'}
                              onClick={() => handleDownload(cert.id, cert.recipient_name)}
                              title={cert.status === 'success' ? 'Download PDF' : 'Not ready yet'}
                              aria-label={`Download certificate for ${cert.recipient_name}`}
                            >
                              <Download size={13} aria-hidden="true" />
                              Download
                            </button>
                          </div>
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
