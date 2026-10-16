import React from 'react';
import type { HealthStatus, ProbeStatus } from '../types';

interface StatusBadgeProps {
  status: HealthStatus | ProbeStatus | string;
  isSimulated?: boolean;
}

export const StatusBadge: React.FC<StatusBadgeProps> = ({ status, isSimulated }) => {
  const norm = String(status).toLowerCase();

  let badgeClass = 'badge-unknown';
  let label = status;

  if (norm === 'healthy' || norm === 'online') {
    badgeClass = 'badge-healthy';
    label = norm === 'online' ? 'ONLINE' : 'HEALTHY';
  } else if (norm === 'degraded' || norm === 'stale') {
    badgeClass = 'badge-degraded';
    label = norm === 'stale' ? 'STALE' : 'DEGRADED';
  } else if (norm === 'failed' || norm === 'unresolved') {
    badgeClass = 'badge-failed';
    label = norm === 'unresolved' ? 'UNRESOLVED' : 'FAILED';
  }

  return (
    <div style={{ display: 'inline-flex', alignItems: 'center', gap: '6px' }}>
      <span className={`badge ${badgeClass}`}>
        <span style={{ width: 6, height: 6, borderRadius: '50%', backgroundColor: 'currentColor' }} />
        {label}
      </span>
      {isSimulated && (
        <span className="badge badge-simulated">
          SIMULATED
        </span>
      )}
    </div>
  );
};
