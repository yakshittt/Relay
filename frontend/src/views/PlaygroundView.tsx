import React, { useState, useEffect } from 'react';
import {
  fetchDemoStatus,
  toggleDemoFault,
  clearAllDemoFaults,
  runDiagnose,
  proposeRecovery,
} from '../api';
import type { DemoStatus, DiagnoseResponse } from '../types';
import { ProbeMatrix } from '../components/ProbeMatrix';
import { StatusBadge } from '../components/StatusBadge';
import { RecoveryModal } from '../components/RecoveryModal';
import {
  Wrench,
  AlertTriangle,
  Play,
  CheckCircle,
  ShieldAlert,
  Loader2,
  Code2,
} from 'lucide-react';

export const PlaygroundView: React.FC = () => {
  const [demoStatus, setDemoStatus] = useState<DemoStatus | null>(null);
  const [latestDiagnosis, setLatestDiagnosis] = useState<DiagnoseResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [activeProposal, setActiveProposal] = useState<any | null>(null);
  const [showRawJson, setShowRawJson] = useState(false);

  const loadStatus = async () => {
    try {
      const status = await fetchDemoStatus();
      setDemoStatus(status);
    } catch (err) {
      console.error('Failed to load demo status', err);
    }
  };

  useEffect(() => {
    loadStatus();
  }, []);

  const handleToggleFault = async (faultType: string, enabled: boolean) => {
    setLoading(true);
    try {
      await toggleDemoFault(faultType, enabled);
      await loadStatus();
    } catch (err: any) {
      alert(`Could not toggle fault: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  const handleClearAll = async () => {
    setLoading(true);
    try {
      await clearAllDemoFaults();
      await loadStatus();
    } catch (err: any) {
      alert(`Could not clear faults: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  const handleRunDiagnostic = async () => {
    setLoading(true);
    try {
      const res = await runDiagnose('jio-lab', 'Playground diagnostic run');
      setLatestDiagnosis(res);
      await loadStatus();
    } catch (err: any) {
      alert(`Diagnostic failed: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  const handleProposeRecovery = async (actionType: string) => {
    if (!latestDiagnosis) return;
    try {
      const proposal = await proposeRecovery(latestDiagnosis.incident_id, actionType, {});
      setActiveProposal(proposal);
    } catch (err: any) {
      alert(`Could not propose recovery: ${err.message}`);
    }
  };

  const faults = demoStatus?.active_faults || {
    dns_outage: false,
    business_http_503: false,
    stale_heartbeat: false,
    gateway_loss: false,
  };

  return (
    <div>
      {/* Demo Warning Banner */}
      <div className="demo-banner">
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <ShieldAlert size={18} style={{ color: 'var(--status-degraded)' }} />
          <span>
            <strong>DEMO SIMULATION ENVIRONMENT ACTIVE</strong> &bull; Injected faults are application-level simulations. They do not alter your host OS, Jio router firmware, or physical Wi-Fi.
          </span>
        </div>
        <button className="btn btn-secondary btn-sm" onClick={handleClearAll} disabled={loading}>
          Reset All Faults
        </button>
      </div>

      <div className="section-header">
        <div>
          <h2 style={{ fontSize: '1.3rem', fontWeight: 700, display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Wrench size={20} style={{ color: 'var(--accent-blue)' }} />
            Diagnostic Playground & Fault Injection Lab
          </h2>
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.84rem' }}>
            Simulate realistic failure scenarios, observe the deterministic diagnosis engine, and execute verified recoveries.
          </p>
        </div>

        <button className="btn btn-primary" onClick={handleRunDiagnostic} disabled={loading}>
          {loading ? <Loader2 size={16} className="animate-spin" /> : <Play size={16} />}
          Run Diagnostic Probes
        </button>
      </div>

      {/* Step 1: Fault Injection Controls */}
      <div className="card">
        <div className="card-header">
          <div className="card-title">
            <AlertTriangle size={16} style={{ color: 'var(--status-degraded)' }} />
            1. Select Simulated Network Fault Scenarios
          </div>
          <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
            Toggle fault on/off then rerun diagnostic probes
          </span>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '16px' }}>
          {/* Fault 1: DNS Outage */}
          <div
            style={{
              backgroundColor: 'var(--bg-card-subtle)',
              border: `1px solid ${faults.dns_outage ? 'var(--status-failed-border)' : 'var(--border-color)'}`,
              borderRadius: 'var(--radius-md)',
              padding: '16px',
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
              <strong>Business Hostname DNS Failure</strong>
              <button
                className={`btn btn-sm ${faults.dns_outage ? 'btn-danger' : 'btn-secondary'}`}
                onClick={() => handleToggleFault('dns_outage', !faults.dns_outage)}
              >
                {faults.dns_outage ? 'Active (Clear)' : 'Inject Fault'}
              </button>
            </div>
            <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
              Simulates name resolution failure for the business application host. Tests Case A & demo recovery.
            </p>
          </div>

          {/* Fault 2: HTTP 503 */}
          <div
            style={{
              backgroundColor: 'var(--bg-card-subtle)',
              border: `1px solid ${faults.business_http_503 ? 'var(--status-failed-border)' : 'var(--border-color)'}`,
              borderRadius: 'var(--radius-md)',
              padding: '16px',
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
              <strong>Business HTTP 503 Outage</strong>
              <button
                className={`btn btn-sm ${faults.business_http_503 ? 'btn-danger' : 'btn-secondary'}`}
                onClick={() => handleToggleFault('business_http_503', !faults.business_http_503)}
              >
                {faults.business_http_503 ? 'Active (Clear)' : 'Inject Fault'}
              </button>
            </div>
            <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
              Simulates general internet working normally, while the specific POS/billing app returns HTTP 503 (Case C).
            </p>
          </div>

          {/* Fault 3: Stale Heartbeat */}
          <div
            style={{
              backgroundColor: 'var(--bg-card-subtle)',
              border: `1px solid ${faults.stale_heartbeat ? 'var(--status-failed-border)' : 'var(--border-color)'}`,
              borderRadius: 'var(--radius-md)',
              padding: '16px',
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
              <strong>ESP32 Stale Heartbeat</strong>
              <button
                className={`btn btn-sm ${faults.stale_heartbeat ? 'btn-danger' : 'btn-secondary'}`}
                onClick={() => handleToggleFault('stale_heartbeat', !faults.stale_heartbeat)}
              >
                {faults.stale_heartbeat ? 'Active (Clear)' : 'Inject Fault'}
              </button>
            </div>
            <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
              Simulates unpowered/offline ESP32 sentinel board while network probes remain operational (Case D).
            </p>
          </div>

          {/* Fault 4: Gateway Loss */}
          <div
            style={{
              backgroundColor: 'var(--bg-card-subtle)',
              border: `1px solid ${faults.gateway_loss ? 'var(--status-failed-border)' : 'var(--border-color)'}`,
              borderRadius: 'var(--radius-md)',
              padding: '16px',
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
              <strong>Gateway Packet Loss</strong>
              <button
                className={`btn btn-sm ${faults.gateway_loss ? 'btn-danger' : 'btn-secondary'}`}
                onClick={() => handleToggleFault('gateway_loss', !faults.gateway_loss)}
              >
                {faults.gateway_loss ? 'Active (Clear)' : 'Inject Fault'}
              </button>
            </div>
            <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
              Simulates local Wi-Fi disconnection from router LAN gateway (Case B).
            </p>
          </div>
        </div>
      </div>

      {/* Step 2: Diagnostic Results & Rule Rationale */}
      {latestDiagnosis && (
        <div className="card">
          <div className="card-header">
            <div className="card-title">
              <CheckCircle size={16} style={{ color: 'var(--accent-blue)' }} />
              2. Evaluated Diagnostic Findings & RCA (Incident #{latestDiagnosis.incident_id})
            </div>
            <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
              <StatusBadge status={latestDiagnosis.status} isSimulated={latestDiagnosis.demo_dns_fault_active} />
              <button
                className="btn btn-secondary btn-sm"
                onClick={() => setShowRawJson(!showRawJson)}
              >
                <Code2 size={12} />
                {showRawJson ? 'Hide JSON' : 'Raw JSON'}
              </button>
            </div>
          </div>

          <div style={{ marginBottom: '16px' }}>
            <h4 style={{ fontSize: '1rem', fontWeight: 600, color: 'var(--text-primary)', marginBottom: '4px' }}>
              {latestDiagnosis.summary}
            </h4>
            <p style={{ fontSize: '0.86rem', color: 'var(--text-secondary)' }}>
              {latestDiagnosis.diagnosis}
            </p>
          </div>

          <ProbeMatrix probes={latestDiagnosis.checks} />

          {showRawJson && (
            <pre
              style={{
                marginTop: '16px',
                padding: '12px',
                backgroundColor: 'var(--bg-input)',
                borderRadius: 'var(--radius-md)',
                fontSize: '0.75rem',
                maxHeight: 240,
                overflowY: 'auto',
                color: 'var(--text-secondary)',
              }}
            >
              {JSON.stringify(latestDiagnosis, null, 2)}
            </pre>
          )}

          {/* Step 3: Recovery Proposal */}
          <div
            style={{
              marginTop: '20px',
              borderTop: '1px solid var(--border-subtle)',
              paddingTop: '16px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
            }}
          >
            <div>
              <div style={{ fontWeight: 600, fontSize: '0.9rem' }}>Recommended Safe Recovery</div>
              <div style={{ fontSize: '0.82rem', color: 'var(--text-muted)' }}>
                {latestDiagnosis.recommended_next_step}
              </div>
            </div>

            <button
              className="btn btn-primary"
              onClick={() => handleProposeRecovery('clear_demo_dns_fault')}
            >
              Propose Authorized Recovery
            </button>
          </div>
        </div>
      )}

      {/* Recovery Modal */}
      {activeProposal && latestDiagnosis && (
        <RecoveryModal
          actionId={activeProposal.action_id}
          incidentId={latestDiagnosis.incident_id}
          actionType={activeProposal.action_type}
          impactDescription={activeProposal.impact_description}
          requiredApprovalLevel={activeProposal.required_approval_level}
          approvalToken={activeProposal.approval_token}
          tokenExpiresAt={activeProposal.token_expires_at}
          onClose={() => setActiveProposal(null)}
          onSuccess={async () => {
            // Rerun diagnostics to show post-recovery verified state
            await handleRunDiagnostic();
          }}
        />
      )}
    </div>
  );
};
