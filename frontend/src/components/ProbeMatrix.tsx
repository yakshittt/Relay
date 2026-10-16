import React from 'react';
import type { ProbeResult } from '../types';
import { StatusBadge } from './StatusBadge';
import { Network, Globe, Shield, Server, Clock } from 'lucide-react';

interface ProbeMatrixProps {
  probes: ProbeResult[];
}

export const ProbeMatrix: React.FC<ProbeMatrixProps> = ({ probes }) => {
  const getIcon = (name: string) => {
    switch (name) {
      case 'gateway_reachability':
        return <Network size={18} style={{ color: 'var(--accent-blue)' }} />;
      case 'dns_resolution':
        return <Globe size={18} style={{ color: 'var(--accent-indigo)' }} />;
      case 'https_egress':
        return <Shield size={18} style={{ color: 'var(--accent-purple)' }} />;
      case 'business_service':
        return <Server size={18} style={{ color: 'var(--status-healthy)' }} />;
      default:
        return <Network size={18} />;
    }
  };

  const formatName = (name: string) => {
    switch (name) {
      case 'gateway_reachability':
        return 'Local Gateway';
      case 'dns_resolution':
        return 'DNS Resolution';
      case 'https_egress':
        return 'HTTPS Egress';
      case 'business_service':
        return 'Business Endpoint';
      default:
        return name;
    }
  };

  if (!probes || probes.length === 0) {
    return (
      <div style={{ padding: '24px', textAlign: 'center', color: 'var(--text-muted)' }}>
        No probe data available. Run diagnostics to collect live measurements.
      </div>
    );
  }

  return (
    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '16px' }}>
      {probes.map((probe, idx) => (
        <div
          key={idx}
          style={{
            backgroundColor: 'var(--bg-card-subtle)',
            border: `1px solid ${probe.ok ? 'var(--border-color)' : 'var(--status-failed-border)'}`,
            borderRadius: 'var(--radius-md)',
            padding: '16px',
            display: 'flex',
            flexDirection: 'column',
            gap: '12px',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              {getIcon(probe.name)}
              <span style={{ fontWeight: 600, fontSize: '0.92rem' }}>
                {formatName(probe.name)}
              </span>
            </div>
            <StatusBadge status={probe.status || (probe.ok ? 'HEALTHY' : 'FAILED')} isSimulated={probe.is_simulated} />
          </div>

          <div>
            <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)', marginBottom: '2px' }}>
              TARGET
            </div>
            <div className="mono" style={{ fontSize: '0.82rem', color: 'var(--text-primary)', wordBreak: 'break-all' }}>
              {probe.target}
            </div>
          </div>

          <div style={{ fontSize: '0.82rem', color: probe.ok ? 'var(--text-secondary)' : 'var(--status-failed)' }}>
            {probe.detail}
          </div>

          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              fontSize: '0.75rem',
              color: 'var(--text-muted)',
              borderTop: '1px solid var(--border-subtle)',
              paddingTop: '8px',
              marginTop: 'auto',
            }}
          >
            <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
              <Clock size={12} />
              Latency: <strong style={{ color: 'var(--text-primary)' }}>{probe.latency_ms} ms</strong>
            </span>
            {probe.error_category && (
              <span style={{ color: 'var(--status-failed)', fontWeight: 600 }}>
                {probe.error_category}
              </span>
            )}
          </div>
        </div>
      ))}
    </div>
  );
};
