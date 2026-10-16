import React, { useState, useEffect } from 'react';
import {
  fetchOverviewStats,
  fetchSites,
  fetchIncidents,
  runDiagnose,
} from '../api';
import type { OverviewStats } from '../types';
import { StatusBadge } from '../components/StatusBadge';
import {
  Building2,
  AlertTriangle,
  Cpu,
  CheckCircle,
  Play,
  ArrowRight,
  RefreshCw,
  Loader2,
} from 'lucide-react';

interface OverviewViewProps {
  onSelectSite: (siteId: string) => void;
  onSelectIncident: (incidentId: number) => void;
  onOpenPlayground: () => void;
}

export const OverviewView: React.FC<OverviewViewProps> = ({
  onSelectSite,
  onSelectIncident,
  onOpenPlayground,
}) => {
  const [stats, setStats] = useState<OverviewStats | null>(null);
  const [sites, setSites] = useState<string[]>([]);
  const [incidents, setIncidents] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [diagnosing, setDiagnosing] = useState(false);
  const [diagReport, setDiagReport] = useState<string>('Routine health verification');

  const loadData = async () => {
    setLoading(true);
    try {
      const [statsData, sitesData, incidentsData] = await Promise.all([
        fetchOverviewStats(),
        fetchSites(),
        fetchIncidents(undefined, undefined),
      ]);
      setStats(statsData);
      setSites(sitesData);
      setIncidents(incidentsData);
    } catch (err) {
      console.error('Failed to load overview data', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
    const interval = setInterval(loadData, 10000); // Polling every 10s
    return () => clearInterval(interval);
  }, []);

  const handleQuickDiagnose = async () => {
    setDiagnosing(true);
    try {
      const res = await runDiagnose('jio-lab', diagReport);
      await loadData();
      onSelectIncident(res.incident_id);
    } catch (err: any) {
      alert(`Diagnostic failed: ${err.message}`);
    } finally {
      setDiagnosing(false);
    }
  };

  return (
    <div>
      {/* Top Banner / Hero Controls */}
      <div className="section-header">
        <div>
          <h2 style={{ fontSize: '1.4rem', fontWeight: 700, letterSpacing: '-0.02em' }}>
            Mission Operations Fleet
          </h2>
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.86rem' }}>
            Live physical telemetry, probe matrix verification, and auditable incident resolutions.
          </p>
        </div>
        <div style={{ display: 'flex', gap: '8px' }}>
          <button className="btn btn-secondary btn-sm" onClick={loadData} disabled={loading}>
            <RefreshCw size={14} className={loading ? 'animate-spin' : ''} />
            Refresh
          </button>
          <button className="btn btn-primary btn-sm" onClick={onOpenPlayground}>
            Launch Demo Fault Simulation
          </button>
        </div>
      </div>

      {/* Aggregate Metrics Grid */}
      <div className="stats-grid">
        <div className="stat-card">
          <div className="stat-header">
            <span>Monitored Sites</span>
            <Building2 size={16} />
          </div>
          <div className="stat-value">{stats ? stats.total_sites : '-'}</div>
          <div className="stat-desc">Locations with active sentinel monitoring</div>
        </div>

        <div className="stat-card">
          <div className="stat-header">
            <span>Open Incidents</span>
            <AlertTriangle size={16} style={{ color: 'var(--status-degraded)' }} />
          </div>
          <div className="stat-value" style={{ color: stats && stats.open_incidents > 0 ? 'var(--status-degraded)' : 'var(--text-primary)' }}>
            {stats ? stats.open_incidents : '-'}
          </div>
          <div className="stat-desc">Requiring investigation or authorized recovery</div>
        </div>

        <div className="stat-card">
          <div className="stat-header">
            <span>Sentinel Hardware</span>
            <Cpu size={16} />
          </div>
          <div className="stat-value">
            <span style={{ color: 'var(--status-healthy)' }}>{stats ? stats.online_devices : 0}</span>
            <span style={{ fontSize: '1rem', color: 'var(--text-muted)' }}> / {stats ? stats.online_devices + stats.stale_devices : 0}</span>
          </div>
          <div className="stat-desc">
            {stats && stats.stale_devices > 0 ? `${stats.stale_devices} hardware monitor(s) stale` : 'All physical sentinels active'}
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-header">
            <span>Recovery Verification</span>
            <CheckCircle size={16} style={{ color: 'var(--status-healthy)' }} />
          </div>
          <div className="stat-value" style={{ color: 'var(--status-healthy)' }}>
            {stats ? `${stats.recovery_success_rate}%` : '-'}
          </div>
          <div className="stat-desc">
            {stats ? `${stats.total_recovery_actions} actions authorized & verified` : 'Audited execution rate'}
          </div>
        </div>
      </div>

      {/* Quick Diagnostic Launcher Card */}
      <div className="card" style={{ background: 'linear-gradient(135deg, var(--bg-card), var(--bg-card-subtle))' }}>
        <div className="card-header">
          <div className="card-title">
            <Play size={16} style={{ color: 'var(--accent-blue)' }} />
            Trigger On-Demand Diagnostic Probe
          </div>
          <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
            Target: <strong>jio-lab (Jio Router LAN)</strong>
          </span>
        </div>
        <div style={{ display: 'flex', gap: '12px', alignItems: 'center' }}>
          <input
            type="text"
            className="input"
            value={diagReport}
            onChange={(e) => setDiagReport(e.target.value)}
            placeholder="Describe observed symptoms, e.g. 'Billing application is not loading'..."
            disabled={diagnosing}
          />
          <button
            className="btn btn-primary"
            style={{ whiteSpace: 'nowrap' }}
            onClick={handleQuickDiagnose}
            disabled={diagnosing || !diagReport.trim()}
          >
            {diagnosing ? (
              <>
                <Loader2 size={16} className="animate-spin" />
                Executing Probes...
              </>
            ) : (
              'Run Diagnostic'
            )}
          </button>
        </div>
      </div>

      {/* Two Column Layout: Sites & Recent Incidents */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(400px, 1fr))', gap: '20px' }}>
        {/* Sites Table */}
        <div className="card">
          <div className="card-header">
            <div className="card-title">
              <Building2 size={16} />
              Monitored Business Sites
            </div>
          </div>
          <div className="table-container">
            <table className="table">
              <thead>
                <tr>
                  <th>Site Identifier</th>
                  <th>Network Profile</th>
                  <th>Sentinel</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                {sites.map((siteId) => (
                  <tr key={siteId}>
                    <td>
                      <strong>{siteId}</strong>
                    </td>
                    <td>Jio Broadband / LAN 192.168.29.1</td>
                    <td>
                      <span className="badge badge-healthy">ESP32 DevKit</span>
                    </td>
                    <td>
                      <button
                        className="btn btn-secondary btn-sm"
                        onClick={() => onSelectSite(siteId)}
                      >
                        Inspect
                        <ArrowRight size={12} />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Incidents Table */}
        <div className="card">
          <div className="card-header">
            <div className="card-title">
              <AlertTriangle size={16} />
              Recent Incidents & Audits
            </div>
          </div>
          <div className="table-container">
            <table className="table">
              <thead>
                <tr>
                  <th>ID</th>
                  <th>Reported Problem</th>
                  <th>Status</th>
                  <th>Time</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                {incidents.length === 0 ? (
                  <tr>
                    <td colSpan={5} style={{ textAlign: 'center', color: 'var(--text-muted)' }}>
                      No recorded incidents. Run a diagnostic above or inject a test fault.
                    </td>
                  </tr>
                ) : (
                  incidents.slice(0, 6).map((inc) => (
                    <tr key={inc.id}>
                      <td className="mono">#{inc.id}</td>
                      <td style={{ maxWidth: 200, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                        {inc.user_report}
                      </td>
                      <td>
                        <StatusBadge status={inc.status} />
                      </td>
                      <td style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>
                        {new Date(inc.created_at).toLocaleTimeString()}
                      </td>
                      <td>
                        <button
                          className="btn btn-secondary btn-sm"
                          onClick={() => onSelectIncident(inc.id)}
                        >
                          View
                        </button>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
};
