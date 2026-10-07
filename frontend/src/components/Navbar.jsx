import React, { useState, useEffect } from 'react';
import { Award, Zap, Layers, BookOpen, Server, Check, X, RefreshCw } from 'lucide-react';

export default function Navbar({ activeTab, setActiveTab, apiBaseUrl, setApiBaseUrl }) {
  const [healthStatus, setHealthStatus] = useState('checking'); // 'online' | 'offline' | 'checking'
  const [showSettings, setShowSettings] = useState(false);
  const [tempUrl, setTempUrl] = useState(apiBaseUrl);

  const checkHealth = async () => {
    try {
      const res = await fetch(`${apiBaseUrl}/health`);
      if (res.ok) {
        setHealthStatus('online');
      } else {
        setHealthStatus('offline');
      }
    } catch {
      setHealthStatus('offline');
    }
  };

  useEffect(() => {
    checkHealth();
    const interval = setInterval(checkHealth, 10000);
    return () => clearInterval(interval);
  }, [apiBaseUrl]);

  const handleSaveSettings = (e) => {
    e.preventDefault();
    setApiBaseUrl(tempUrl.trim().replace(/\/$/, ''));
    setShowSettings(false);
  };

  return (
    <header className="navbar" role="banner">
      <div className="nav-content">
        {/* Brand */}
        <div 
          className="brand-wrapper" 
          onClick={() => setActiveTab('generate')}
          role="button"
          tabIndex={0}
          onKeyDown={(e) => e.key === 'Enter' && setActiveTab('generate')}
          aria-label="CertForge Home"
        >
          <div className="brand-icon-box" aria-hidden="true">
            <Award size={18} />
          </div>
          <div className="brand-title">
            Cert<span>Forge</span>
          </div>
        </div>

        {/* Navigation Tabs */}
        <nav className="nav-tabs" role="tablist" aria-label="Main Application Tabs">
          <button
            role="tab"
            aria-selected={activeTab === 'generate'}
            className={`nav-tab-btn ${activeTab === 'generate' ? 'active' : ''}`}
            onClick={() => setActiveTab('generate')}
          >
            <Zap size={14} aria-hidden="true" />
            Bulk Generator
          </button>
          <button
            role="tab"
            aria-selected={activeTab === 'tracker'}
            className={`nav-tab-btn ${activeTab === 'tracker' ? 'active' : ''}`}
            onClick={() => setActiveTab('tracker')}
          >
            <Layers size={14} aria-hidden="true" />
            Job Tracker
          </button>
          <button
            role="tab"
            aria-selected={activeTab === 'preview'}
            className={`nav-tab-btn ${activeTab === 'preview' ? 'active' : ''}`}
            onClick={() => setActiveTab('preview')}
          >
            <Award size={14} aria-hidden="true" />
            Template Inspector
          </button>
          <button
            role="tab"
            aria-selected={activeTab === 'docs'}
            className={`nav-tab-btn ${activeTab === 'docs' ? 'active' : ''}`}
            onClick={() => setActiveTab('docs')}
          >
            <BookOpen size={14} aria-hidden="true" />
            API & Specs
          </button>
        </nav>

        {/* Actions & Health Status */}
        <div className="nav-right-actions">
          <button
            className="health-status"
            onClick={checkHealth}
            title="Click to re-verify backend API health"
            aria-label={`API Status: ${healthStatus}. Click to re-check.`}
            type="button"
          >
            <span 
              className={`status-dot ${healthStatus}`} 
              aria-hidden="true"
            />
            <span>
              {healthStatus === 'online' ? 'Connected' : healthStatus === 'offline' ? 'Offline' : 'Connecting…'}
            </span>
          </button>

          <button
            className="btn btn-outline btn-sm"
            onClick={() => setShowSettings(!showSettings)}
            aria-expanded={showSettings}
            aria-label="Configure API Endpoint"
            type="button"
          >
            <Server size={13} aria-hidden="true" />
            <span>Endpoint</span>
          </button>
        </div>
      </div>

      {/* Backend URL Configuration Drawer */}
      {showSettings && (
        <div
          style={{
            backgroundColor: 'var(--bg-subtle)',
            borderBottom: '1px solid var(--border-default)',
            padding: '0.75rem 1.5rem',
          }}
          role="region"
          aria-label="API Server Configuration"
        >
          <form
            onSubmit={handleSaveSettings}
            style={{
              maxWidth: '1200px',
              margin: '0 auto',
              display: 'flex',
              alignItems: 'center',
              gap: '0.75rem',
              flexWrap: 'wrap',
            }}
          >
            <label 
              htmlFor="backend-url-input" 
              style={{ fontSize: '0.8125rem', color: 'var(--text-secondary)', fontWeight: 500 }}
            >
              Backend URL:
            </label>
            <input
              id="backend-url-input"
              type="text"
              value={tempUrl}
              onChange={(e) => setTempUrl(e.target.value)}
              className="form-input"
              style={{ maxWidth: '320px', padding: '0.375rem 0.625rem', fontSize: '0.8125rem' }}
              placeholder="http://127.0.0.1:8000"
            />
            <button type="submit" className="btn btn-primary btn-sm">
              <Check size={13} aria-hidden="true" />
              Save
            </button>
            <button
              type="button"
              className="btn btn-outline btn-sm"
              onClick={() => {
                setTempUrl('');
                setApiBaseUrl('');
                setShowSettings(false);
              }}
            >
              Proxy Mode ('')
            </button>
            <button
              type="button"
              className="btn btn-outline btn-sm"
              onClick={() => setShowSettings(false)}
            >
              <X size={13} aria-hidden="true" />
              Cancel
            </button>
          </form>
        </div>
      )}
    </header>
  );
}
