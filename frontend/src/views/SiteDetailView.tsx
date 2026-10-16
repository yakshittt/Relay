import React, { useState, useEffect } from 'react';
import { fetchSiteStatus, runDiagnose, fetchIncidents } from '../api';
import { ProbeMatrix } from '../components/ProbeMatrix';
import { StatusBadge } from '../components/StatusBadge';
import {
  ShieldCheck,
  Cpu,
  Wifi,
  Server,
  RefreshCw,
  Play,
  Clock,
  ArrowLeft,
  Loader2,
} from 'lucide-react';

interface SiteDetailViewProps {
  siteId: string;
  onBack: () => void;
  onSelectIncident: (incidentId: number) => void;
}

export const SiteDetailView: React.FC<SiteDetailViewProps> = ({
  siteId,
  onBack,
  onSelectIncident,
}) => {
  const [siteData, setSiteData] = useState<any | null>(null);
  const [incidents, setIncidents] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [diagnosing, setDiagnosing] = useState(false);

  const loadData = async () => {
    setLoading(true);
    try {
      const [statusRes, incList] = await Promise.all([
        fetchSiteStatus(siteId),
        fetchIncidents(siteId, undefined),
      ]);
      setSiteData(statusRes);
      setIncidents(incList);
    } catch (err) {
      console.error('Failed to load site details', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [siteId]);

  const handleRunDiagnostics = async () => {
    setDiagnosing(true);
    try {
      const res = await runDiagnose(siteId, 'Routine comprehensive site probe inspection');
      await loadData();
      onSelectIncident(res.incident_id);
    } catch (err: any) {
      alert(`Diagnostics failed: ${err.message}`);
    } finally {
      setDiagnosing(false);
    }
  };

  const latestInc = siteData?.latest_incident;
  const latestReport = latestInc?.report;
  const probes = latestReport?.checks || [];
  const devices = siteData?.devices || [];

  return (
    <div>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '20px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <button className="btn btn-secondary btn-sm" onClick={onBack}>
            <ArrowLeft size={14} />
            Back
          </button>
          <div>
            <h2 style={{ fontSize: '1.3rem', fontWeight: 700 }}>
              Site Inspection: <span className="mono">{siteId}</span>
            </h2>
            <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
              Physical observation environment: Jio Broadband Home Router LAN
            </div>
          </div>
        </div>

        <div style={{ display: 'flex', gap: '8px' }}>
          <button className="btn btn-secondary btn-sm" onClick={loadData} disabled={loading}>
            <RefreshCw size={14} className={loading ? 'animate-spin' : ''} />
            Refresh
          </button>
          <button className="btn btn-primary btn-sm" onClick={handleRunDiagnostics} disabled={diagnosing}>
            {diagnosing ? (
              <>
                <Loader2 size={14} className="animate-spin" />
                Probing Site...
              </>
            ) : (
              <>
                <Play size={14} />
                Run Fresh Probes
              </>
            )}
          </button>
        </div>
      </div>

      {/* Hardware Telemetry Card */}
      <div className="card">
        <div className="card-header">
          <div className="card-title">
            <Cpu size={16} style={{ color: 'var(--accent-blue)' }} />
            Physical Hardware Sentinels (ESP32 DevKit)
          </div>
          <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
            Out-of-band physical heartbeat presence monitor
          </span>
        </div>

        {devices.length === 0 ? (
          <div style={{ padding: '16px', color: 'var(--text-muted)', fontSize: '0.86rem' }}>
            No hardware sentinels currently reporting heartbeats for this site.
            (Check ESP32 power or flash firmware from <code>firmware/relay_esp32.ino</code>).
          </div>
        ) : (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '16px' }}>
            {devices.map((dev: any) => (
              <div
                key={dev.device_id}
                style={{
                  backgroundColor: 'var(--bg-card-subtle)',
                  border: '1px solid var(--border-color)',
                  borderRadius: 'var(--radius-md)',
                  padding: '16px',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '10px',
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span className="mono" style={{ fontWeight: 600, fontSize: '0.9rem' }}>
                    {dev.device_id}
                  </span>
                  <StatusBadge status={dev.status} />
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px', fontSize: '0.8rem' }}>
                  <div>
                    <span style={{ color: 'var(--text-muted)' }}>Wi-Fi RSSI:</span>
                    <div style={{ fontWeight: 600, display: 'flex', alignItems: 'center', gap: '4px' }}>
                      <Wifi size={12} />
                      {dev.wifi_rssi_dbm ? `${dev.wifi_rssi_dbm} dBm` : 'N/A'}
                    </div>
                  </div>
                  <div>
                    <span style={{ color: 'var(--text-muted)' }}>Uptime:</span>
                    <div style={{ fontWeight: 600, display: 'flex', alignItems: 'center', gap: '4px' }}>
                      <Clock size={12} />
                      {dev.uptime_seconds ? `${dev.uptime_seconds}s` : 'N/A'}
                    </div>
                  </div>
                  <div>
                    <span style={{ color: 'var(--text-muted)' }}>Firmware:</span>
                    <div>{dev.firmware_version || '1.2.0'}</div>
                  </div>
                  <div>
                    <span style={{ color: 'var(--text-muted)' }}>Heartbeat Age:</span>
                    <div>{dev.age_seconds !== null ? `${dev.age_seconds}s ago` : 'N/A'}</div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Live Probe Matrix */}
      <div className="card">
        <div className="card-header">
          <div className="card-title">
            <ShieldCheck size={16} style={{ color: 'var(--status-healthy)' }} />
            Diagnostic Probe Matrix (Latest Run)
          </div>
          {latestInc && (
            <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
              Incident #{latestInc.id} &bull; Recorded at {new Date(latestInc.created_at).toLocaleTimeString()}
            </span>
          )}
        </div>
        <ProbeMatrix probes={probes} />
      </div>

      {/* Incident History Table for this site */}
      <div className="card">
        <div className="card-header">
          <div className="card-title">
            <Server size={16} />
            Site Incident History & Audit Records
          </div>
        </div>
        <div className="table-container">
          <table className="table">
            <thead>
              <tr>
                <th>ID</th>
                <th>Status</th>
                <th>Reported Issue</th>
                <th>Diagnosis Summary</th>
                <th>Time</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              {incidents.length === 0 ? (
                <tr>
                  <td colSpan={6} style={{ textAlign: 'center', color: 'var(--text-muted)' }}>
                    No incident records for this site.
                  </td>
                </tr>
              ) : (
                incidents.map((inc) => (
                  <tr key={inc.id}>
                    <td className="mono">#{inc.id}</td>
                    <td>
                      <StatusBadge status={inc.status} />
                    </td>
                    <td>{inc.user_report}</td>
                    <td style={{ color: 'var(--text-secondary)' }}>{inc.summary || inc.diagnosis}</td>
                    <td style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>
                      {new Date(inc.created_at).toLocaleString()}
                    </td>
                    <td>
                      <button
                        className="btn btn-secondary btn-sm"
                        onClick={() => onSelectIncident(inc.id)}
                      >
                        Inspect RCA
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
  );
};
