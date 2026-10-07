import React, { useState } from 'react';
import { 
  Plus, 
  Trash2, 
  Sparkles, 
  Upload, 
  FileSpreadsheet, 
  Send, 
  CheckCircle, 
  Copy, 
  ArrowRight, 
  Users, 
  Calendar, 
  Building, 
  Bookmark,
  FileText,
  Download,
  HelpCircle
} from 'lucide-react';

const SAMPLE_COHORT = [
  { recipient_name: "Alice Johnson", recipient_email: "alice.johnson@example.com", course_name: "Autonomous Drone Systems & Aerial Mapping" },
  { recipient_name: "Bob Smith", recipient_email: "bob.smith@example.com", course_name: "Computer Vision & LiDAR Point Clouds" },
  { recipient_name: "Catherine Vance", recipient_email: "catherine.v@example.com", course_name: "Geospatial Photogrammetry & Orthomosaics" },
  { recipient_name: "David Kumar", recipient_email: "david.kumar@example.com", course_name: "Drone Fleet Operations & Regulatory Compliance" },
  { recipient_name: "Elena Rostova", recipient_email: "elena.rostova@example.com", course_name: "Thermal Inspection & Pipeline Monitoring" }
];

export default function Generator({ apiBaseUrl, onJobSubmitted, addToast }) {
  const today = new Date().toISOString().split('T')[0];

  const [eventName, setEventName] = useState('Aereo Advanced Drone Tech Cohort 2024');
  const [issuerName, setIssuerName] = useState('Aereo Academy');
  const [issueDate, setIssueDate] = useState(today);

  const [inputMode, setInputMode] = useState('form'); // 'form' | 'csv'
  const [recipients, setRecipients] = useState([
    { recipient_name: 'Alice Johnson', recipient_email: 'alice@example.com', course_name: 'Python for Geospatial Data' },
    { recipient_name: 'Bob Smith', recipient_email: 'bob@example.com', course_name: 'Autonomous Navigation Algorithms' }
  ]);
  const [csvText, setCsvText] = useState('');

  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submittedJob, setSubmittedJob] = useState(null);

  // Form row actions
  const handleRecipientChange = (index, field, value) => {
    const updated = [...recipients];
    updated[index][field] = value;
    setRecipients(updated);
  };

  const handleAddRecipient = () => {
    setRecipients([
      ...recipients,
      { recipient_name: '', recipient_email: '', course_name: recipients[recipients.length - 1]?.course_name || '' }
    ]);
  };

  const handleRemoveRecipient = (index) => {
    if (recipients.length === 1) {
      addToast({ type: 'error', message: 'At least one recipient is required.' });
      return;
    }
    setRecipients(recipients.filter((_, i) => i !== index));
  };

  const handleLoadSample = () => {
    setRecipients(SAMPLE_COHORT);
    setEventName('Aereo Geospatial & UAV Engineering Fellowship');
    setIssuerName('Aereo Aerospace Institute');
    addToast({ type: 'info', message: 'Loaded 5 sample recipients!' });
  };

  const handleParseCsv = () => {
    if (!csvText.trim()) {
      addToast({ type: 'error', message: 'Please paste CSV content first.' });
      return;
    }

    const lines = csvText.trim().split('\n');
    const parsed = [];

    for (let i = 0; i < lines.length; i++) {
      const line = lines[i].trim();
      if (!line) continue;
      // Skip header row if present
      if (i === 0 && (line.toLowerCase().includes('name') || line.toLowerCase().includes('email'))) {
        continue;
      }

      const parts = line.split(',').map(p => p.trim().replace(/^["']|["']$/g, ''));
      if (parts.length >= 3) {
        parsed.push({
          recipient_name: parts[0],
          recipient_email: parts[1],
          course_name: parts[2]
        });
      } else if (parts.length === 2) {
        parsed.push({
          recipient_name: parts[0],
          recipient_email: parts[1],
          course_name: 'Certificate of Achievement'
        });
      }
    }

    if (parsed.length === 0) {
      addToast({ type: 'error', message: 'Could not parse any valid recipients. Format: Name, Email, Course' });
      return;
    }

    setRecipients(parsed);
    setInputMode('form');
    addToast({ type: 'success', message: `Successfully imported ${parsed.length} recipients from CSV!` });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();

    if (!eventName.trim() || !issuerName.trim() || !issueDate) {
      addToast({ type: 'error', message: 'Please complete all Event Details.' });
      return;
    }

    const cleanedRecipients = recipients
      .map(r => ({
        recipient_name: r.recipient_name.trim(),
        recipient_email: r.recipient_email.trim(),
        course_name: r.course_name.trim()
      }))
      .filter(r => r.recipient_name && r.recipient_email && r.course_name);

    if (cleanedRecipients.length === 0) {
      addToast({ type: 'error', message: 'Please provide at least one valid recipient with Name, Email, and Course.' });
      return;
    }

    // Email format validation
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    for (const r of cleanedRecipients) {
      if (!emailRegex.test(r.recipient_email)) {
        addToast({ type: 'error', message: `Invalid email address: ${r.recipient_email}` });
        return;
      }
    }

    setIsSubmitting(true);

    try {
      const payload = {
        event_name: eventName.trim(),
        issuer_name: issuerName.trim(),
        issue_date: issueDate,
        recipients: cleanedRecipients
      };

      const endpoint = `${apiBaseUrl}/api/v1/jobs`;
      const response = await fetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || `Server returned error status ${response.status}`);
      }

      const result = await response.json();
      setSubmittedJob(result);
      addToast({
        type: 'success',
        title: 'Job Accepted',
        message: `${result.total_count} certificate(s) queued for generation.`
      });

    } catch (err) {
      addToast({
        type: 'error',
        title: 'Submission Failed',
        message: err.message || 'Could not connect to FastAPI server.'
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleCopyJobId = () => {
    if (submittedJob?.job_id) {
      navigator.clipboard.writeText(submittedJob.job_id);
      addToast({ type: 'info', message: 'Job ID copied to clipboard!' });
    }
  };

  return (
    <div className="fade-in">
      {/* Clean SaaS Hero Banner */}
      <section className="hero-banner" aria-labelledby="hero-heading">
        <div className="hero-badge-tag">
          <Sparkles size={12} aria-hidden="true" />
          <span>Asynchronous Certificate Engine</span>
        </div>
        <h1 id="hero-heading" className="hero-title">
          Bulk PDF Certificate Generator
        </h1>
        <p className="hero-subtitle">
          Configure event details, provide recipients via form or CSV, and let our ReportLab backend generate vector-crisp certificates asynchronously.
        </p>
      </section>

      {/* How This Works Section */}
      <section className="how-it-works-section" aria-labelledby="how-it-works-heading">
        <div className="how-it-works-header">
          <div className="how-it-works-title">
            <HelpCircle size={17} aria-hidden="true" />
            <span id="how-it-works-heading">How This Works</span>
          </div>
          <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
            Follow these 4 simple steps to generate and download certificates
          </span>
        </div>

        <div className="how-it-works-grid">
          <div className="how-it-works-card">
            <div className="how-step-top">
              <span className="how-step-num">STEP 01</span>
              <div className="how-step-icon">
                <Building size={14} aria-hidden="true" />
              </div>
            </div>
            <div className="how-step-title">Event & Issuer Info</div>
            <p className="how-step-desc">
              Specify the event name, organization, and issue date. Or click <strong>Fill Sample Data</strong> for instant testing.
            </p>
          </div>

          <div className="how-it-works-card">
            <div className="how-step-top">
              <span className="how-step-num">STEP 02</span>
              <div className="how-step-icon">
                <Users size={14} aria-hidden="true" />
              </div>
            </div>
            <div className="how-step-title">Add Recipients</div>
            <p className="how-step-desc">
              Enter participant details row-by-row in the form grid, or paste a list directly into the <strong>Bulk CSV Importer</strong>.
            </p>
          </div>

          <div className="how-it-works-card">
            <div className="how-step-top">
              <span className="how-step-num">STEP 03</span>
              <div className="how-step-icon">
                <Send size={14} aria-hidden="true" />
              </div>
            </div>
            <div className="how-step-title">Dispatch Bulk Job</div>
            <p className="how-step-desc">
              Click dispatch to submit. The backend immediately accepts the job (HTTP 202) and queues generation in the background.
            </p>
          </div>

          <div className="how-it-works-card">
            <div className="how-step-top">
              <span className="how-step-num">STEP 04</span>
              <div className="how-step-icon">
                <Download size={14} aria-hidden="true" />
              </div>
            </div>
            <div className="how-step-title">Track & Download</div>
            <p className="how-step-desc">
              Monitor real-time progress counters in the <strong>Job Tracker</strong>, preview certificate layouts, and download PDF files.
            </p>
          </div>
        </div>
      </section>

      {/* Success Notification Card */}
      {submittedJob && (
        <div 
          className="glass-panel" 
          style={{ padding: '1.5rem', marginBottom: '1.75rem', borderLeft: '4px solid #09090b' }}
          role="status"
          aria-live="polite"
        >
          <div style={{ display: 'flex', alignItems: 'flex-start', gap: '1rem', justifyContent: 'space-between', flexWrap: 'wrap' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
              <div 
                style={{ 
                  width: '36px', 
                  height: '36px', 
                  borderRadius: 'var(--radius-sm)', 
                  backgroundColor: 'var(--bg-muted)', 
                  display: 'flex', 
                  alignItems: 'center', 
                  justifyContent: 'center', 
                  color: 'var(--text-primary)' 
                }}
              >
                <CheckCircle size={20} aria-hidden="true" />
              </div>
              <div>
                <h3 style={{ fontSize: '1rem', fontWeight: 600, color: 'var(--text-primary)' }}>
                  Job Dispatched Successfully
                </h3>
                <p style={{ color: 'var(--text-secondary)', fontSize: '0.8125rem' }}>
                  {submittedJob.message}
                </p>
              </div>
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <button
                type="button"
                className="btn btn-outline btn-sm"
                onClick={handleCopyJobId}
                aria-label="Copy Job UUID"
              >
                <Copy size={13} aria-hidden="true" />
                Copy ID
              </button>
              <button
                type="button"
                className="btn btn-primary btn-sm"
                onClick={() => onJobSubmitted(submittedJob.job_id)}
              >
                Track Live Progress
                <ArrowRight size={13} aria-hidden="true" />
              </button>
            </div>
          </div>

          <div 
            style={{ 
              marginTop: '1rem', 
              padding: '0.625rem 0.875rem', 
              backgroundColor: 'var(--bg-subtle)', 
              borderRadius: 'var(--radius-sm)', 
              border: '1px solid var(--border-default)', 
              display: 'flex', 
              alignItems: 'center', 
              gap: '0.75rem' 
            }}
          >
            <span style={{ fontSize: '0.6875rem', fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
              JOB UUID:
            </span>
            <code style={{ fontFamily: 'var(--font-mono)', fontSize: '0.8125rem', color: 'var(--text-primary)' }}>
              {submittedJob.job_id}
            </code>
          </div>
        </div>
      )}

      <form onSubmit={handleSubmit} className="generator-grid" noValidate>
        {/* Section 1: Event & Issuer Configuration */}
        <div className="glass-panel" style={{ padding: '1.5rem' }}>
          <div className="section-header-box">
            <h2 className="section-title-sm">
              <Building size={16} aria-hidden="true" />
              1. Event & Issuer Specification
            </h2>
            <button
              type="button"
              className="btn btn-outline btn-sm"
              onClick={handleLoadSample}
            >
              <Sparkles size={13} aria-hidden="true" />
              Fill Sample Data
            </button>
          </div>

          <div className="grid-3">
            <div className="form-group">
              <label htmlFor="event-name-input" className="form-label">
                <Bookmark size={13} aria-hidden="true" /> Event / Program Name *
              </label>
              <input
                id="event-name-input"
                type="text"
                className="form-input"
                placeholder="e.g. UAV Flight Mechanics Summit"
                value={eventName}
                onChange={(e) => setEventName(e.target.value)}
                required
              />
            </div>

            <div className="form-group">
              <label htmlFor="issuer-name-input" className="form-label">
                <Building size={13} aria-hidden="true" /> Issuing Organization *
              </label>
              <input
                id="issuer-name-input"
                type="text"
                className="form-input"
                placeholder="e.g. Aereo Aerospace Academy"
                value={issuerName}
                onChange={(e) => setIssuerName(e.target.value)}
                required
              />
            </div>

            <div className="form-group">
              <label htmlFor="issue-date-input" className="form-label">
                <Calendar size={13} aria-hidden="true" /> Issue Date *
              </label>
              <input
                id="issue-date-input"
                type="date"
                className="form-input"
                value={issueDate}
                onChange={(e) => setIssueDate(e.target.value)}
                required
              />
            </div>
          </div>
        </div>

        {/* Section 2: Recipients List */}
        <div className="glass-panel" style={{ padding: '1.5rem' }}>
          <div className="section-header-box">
            <h2 className="section-title-sm">
              <Users size={16} aria-hidden="true" />
              2. Recipients Cohort ({recipients.length} Recipient{recipients.length === 1 ? '' : 's'})
            </h2>

            <div style={{ display: 'flex', gap: '0.375rem' }}>
              <button
                type="button"
                className={`btn btn-sm ${inputMode === 'form' ? 'btn-secondary' : 'btn-outline'}`}
                onClick={() => setInputMode('form')}
              >
                <Users size={13} aria-hidden="true" /> Form Grid
              </button>
              <button
                type="button"
                className={`btn btn-sm ${inputMode === 'csv' ? 'btn-secondary' : 'btn-outline'}`}
                onClick={() => setInputMode('csv')}
              >
                <FileSpreadsheet size={13} aria-hidden="true" /> CSV Importer
              </button>
            </div>
          </div>

          {inputMode === 'csv' ? (
            <div style={{ marginBottom: '1.25rem' }}>
              <p style={{ fontSize: '0.8125rem', color: 'var(--text-secondary)', marginBottom: '0.625rem' }}>
                Paste comma-separated rows formatted as: <code style={{ backgroundColor: 'var(--bg-muted)', padding: '0.125rem 0.375rem', borderRadius: 'var(--radius-xs)' }}>Full Name, Email Address, Course Name</code>
              </p>
              <textarea
                className="form-textarea"
                rows={6}
                placeholder="Alice Johnson, alice@example.com, Autonomous Navigation&#10;Bob Smith, bob@example.com, Computer Vision & LiDAR"
                value={csvText}
                onChange={(e) => setCsvText(e.target.value)}
                aria-label="CSV input data"
              />
              <div style={{ marginTop: '0.75rem', display: 'flex', gap: '0.625rem', flexWrap: 'wrap' }}>
                <button
                  type="button"
                  className="btn btn-primary btn-sm"
                  onClick={handleParseCsv}
                >
                  <Upload size={13} aria-hidden="true" /> Parse & Load Recipients
                </button>
                <button
                  type="button"
                  className="btn btn-outline btn-sm"
                  onClick={() => setCsvText("Alice Johnson, alice@example.com, Flight Planning & Safety\nBob Smith, bob@example.com, LiDAR Point Cloud Analytics")}
                >
                  Load Example CSV
                </button>
              </div>
            </div>
          ) : (
            <div>
              {recipients.map((r, idx) => (
                <div key={idx} className="recipient-card">
                  <div className="recipient-card-header">
                    <span className="recipient-index-badge">
                      #{idx + 1}
                    </span>
                    <button
                      type="button"
                      className="btn btn-danger btn-sm"
                      onClick={() => handleRemoveRecipient(idx)}
                      title={`Remove recipient #${idx + 1}`}
                      aria-label={`Remove recipient #${idx + 1}`}
                      style={{ padding: '0.25rem 0.5rem' }}
                    >
                      <Trash2 size={13} aria-hidden="true" />
                    </button>
                  </div>

                  <div className="grid-3">
                    <div className="form-group" style={{ marginBottom: 0 }}>
                      <label className="form-label" style={{ fontSize: '0.75rem' }}>Recipient Full Name *</label>
                      <input
                        type="text"
                        className="form-input"
                        placeholder="e.g. John Doe"
                        value={r.recipient_name}
                        onChange={(e) => handleRecipientChange(idx, 'recipient_name', e.target.value)}
                        required
                        aria-label={`Recipient ${idx + 1} name`}
                      />
                    </div>
                    <div className="form-group" style={{ marginBottom: 0 }}>
                      <label className="form-label" style={{ fontSize: '0.75rem' }}>Email Address *</label>
                      <input
                        type="email"
                        className="form-input"
                        placeholder="john.doe@example.com"
                        value={r.recipient_email}
                        onChange={(e) => handleRecipientChange(idx, 'recipient_email', e.target.value)}
                        required
                        aria-label={`Recipient ${idx + 1} email`}
                      />
                    </div>
                    <div className="form-group" style={{ marginBottom: 0 }}>
                      <label className="form-label" style={{ fontSize: '0.75rem' }}>Course / Specialization *</label>
                      <input
                        type="text"
                        className="form-input"
                        placeholder="e.g. UAV Flight Mechanics"
                        value={r.course_name}
                        onChange={(e) => handleRecipientChange(idx, 'course_name', e.target.value)}
                        required
                        aria-label={`Recipient ${idx + 1} course name`}
                      />
                    </div>
                  </div>
                </div>
              ))}

              <div style={{ marginTop: '1rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '0.75rem' }}>
                <button
                  type="button"
                  className="btn btn-outline btn-sm"
                  onClick={handleAddRecipient}
                >
                  <Plus size={13} aria-hidden="true" /> Add Recipient Row
                </button>

                <span style={{ fontSize: '0.8125rem', color: 'var(--text-muted)' }}>
                  Total: {recipients.length} certificates to generate
                </span>
              </div>
            </div>
          )}

          {/* Submit Action */}
          <div 
            style={{ 
              marginTop: '1.75rem', 
              paddingTop: '1.25rem', 
              borderTop: '1px solid var(--border-default)', 
              display: 'flex', 
              justifyContent: 'space-between', 
              gap: '1rem', 
              alignItems: 'center',
              flexWrap: 'wrap'
            }}
          >
            <span style={{ fontSize: '0.8125rem', color: 'var(--text-muted)' }}>
              Processed in background via FastAPI BackgroundTasks & ReportLab
            </span>
            <button
              type="submit"
              className="btn btn-primary btn-lg"
              disabled={isSubmitting}
            >
              {isSubmitting ? (
                <>
                  <div className="status-dot online animate-spin" style={{ width: '10px', height: '10px' }} aria-hidden="true" />
                  <span>Submitting Job…</span>
                </>
              ) : (
                <>
                  <Send size={15} aria-hidden="true" />
                  <span>Dispatch Bulk Job ({recipients.length})</span>
                </>
              )}
            </button>
          </div>
        </div>
      </form>
    </div>
  );
}
