import React, { useState } from 'react';
import { Activity, Radio, Settings, ShieldCheck, Wrench } from 'lucide-react';
import { getApiBaseUrl, getApiToken, setApiBaseUrl, setApiToken } from '../api';

interface NavbarProps {
  activeTab: string;
  setActiveTab: (tab: string) => void;
  backendHealthy: boolean | null;
  demoMode: boolean;
}

export const Navbar: React.FC<NavbarProps> = ({
  activeTab,
  setActiveTab,
  backendHealthy,
  demoMode,
}) => {
  const [showSettings, setShowSettings] = useState(false);
  const [urlInput, setUrlInput] = useState(getApiBaseUrl());
  const [tokenInput, setTokenInput] = useState(getApiToken());

  const handleSaveSettings = () => {
    setApiBaseUrl(urlInput.trim());
    setApiToken(tokenInput.trim());
    setShowSettings(false);
    window.location.reload();
  };

  return (
    <>
      <header className="navbar">
        <div className="nav-brand">
          <div className="brand-badge">
            <Radio size={14} />
            RELAY
          </div>
          <div>
            <span className="brand-title">Incident Sentinel</span>
            <span className="brand-subtitle">Voice-Native Ops</span>
          </div>
        </div>

        <nav className="nav-links">
          <button
            className={`nav-item ${activeTab === 'overview' ? 'active' : ''}`}
            onClick={() => setActiveTab('overview')}
          >
            <Activity size={16} />
            Overview
          </button>
          <button
            className={`nav-item ${activeTab === 'site' ? 'active' : ''}`}
            onClick={() => setActiveTab('site')}
          >
            <ShieldCheck size={16} />
            Site Lab
          </button>
          <button
            className={`nav-item ${activeTab === 'voice' ? 'active' : ''}`}
            onClick={() => setActiveTab('voice')}
          >
            <Radio size={16} />
            Voice Console
          </button>
          <button
            className={`nav-item ${activeTab === 'playground' ? 'active' : ''}`}
            onClick={() => setActiveTab('playground')}
          >
            <Wrench size={16} />
            Playground
          </button>
        </nav>

        <div className="nav-actions">
          {demoMode && (
            <span className="badge badge-simulated" title="Demo mode enabled on backend">
              DEMO MODE
            </span>
          )}

          <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.8rem' }}>
            <span
              style={{
                width: 8,
                height: 8,
                borderRadius: '50%',
                backgroundColor: backendHealthy ? 'var(--status-healthy)' : 'var(--status-failed)',
              }}
            />
            <span style={{ color: 'var(--text-secondary)' }}>
              {backendHealthy ? 'API Connected' : 'API Offline'}
            </span>
          </div>

          <button
            className="btn btn-secondary btn-sm"
            onClick={() => setShowSettings(true)}
            title="Configure API Connection"
          >
            <Settings size={14} />
          </button>
        </div>
      </header>

      {showSettings && (
        <div className="modal-overlay" onClick={() => setShowSettings(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h3 className="modal-title">API Connection Settings</h3>
              <button
                style={{ background: 'none', border: 'none', color: 'var(--text-muted)', cursor: 'pointer', fontSize: '1.2rem' }}
                onClick={() => setShowSettings(false)}
              >
                &times;
              </button>
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
              <div>
                <label style={{ fontSize: '0.82rem', color: 'var(--text-secondary)', display: 'block', marginBottom: '6px' }}>
                  Backend API Base URL
                </label>
                <input
                  type="text"
                  className="input"
                  value={urlInput}
                  onChange={(e) => setUrlInput(e.target.value)}
                  placeholder="http://localhost:8000"
                />
              </div>
              <div>
                <label style={{ fontSize: '0.82rem', color: 'var(--text-secondary)', display: 'block', marginBottom: '6px' }}>
                  Bearer API Token
                </label>
                <input
                  type="password"
                  className="input"
                  value={tokenInput}
                  onChange={(e) => setTokenInput(e.target.value)}
                  placeholder="relay-dev-token-secret-2026"
                />
              </div>
              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '8px', marginTop: '10px' }}>
                <button className="btn btn-secondary" onClick={() => setShowSettings(false)}>
                  Cancel
                </button>
                <button className="btn btn-primary" onClick={handleSaveSettings}>
                  Save & Reconnect
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </>
  );
};
