import React, { useState, useEffect } from 'react';
import { fetchIncidentDetail, proposeRecovery } from '../api';
import type { IncidentDetail, RecoveryAction } from '../types';
import { StatusBadge } from '../components/StatusBadge';
import { ProbeMatrix } from '../components/ProbeMatrix';
import { RecoveryModal } from '../components/RecoveryModal';
import {
  AlertTriangle,
  ArrowLeft,
  Clock,
  CheckCircle,
  HelpCircle,
  Wrench,
  Loader2,
  FileText,
} from 'lucide-react';

interface IncidentDetailViewProps {
  incidentId: number;
  onBack: () => void;
}

export const IncidentDetailView: React.FC<IncidentDetailViewProps> = ({
  incidentId,
  onBack,
}) => {
  const [incident, setIncident] = useState<IncidentDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [proposing, setProposing] = useState(false);
  const [activeProposal, setActiveProposal] = useState<any | null>(null);

  const loadIncident = async () => {
    setLoading(true);
    try {
      const data = await fetchIncidentDetail(incidentId);
      setIncident(data);
    } catch (err) {
      console.error('Failed to load incident details', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadIncident();
  }, [incidentId]);

  const handleProposeAction = async (actionType: string) => {
    setProposing(true);
    try {
      const proposal = await proposeRecovery(incidentId, actionType, {});
      setActiveProposal(proposal);
      await loadIncident();
    } catch (err: any) {
      alert(`Could not propose recovery: ${err.message}`);
    } finally {
      setProposing(false);
    }
  };

  if (loading) {
    return (
      <div style={{ textAlign: 'center', padding: '60px 0', color: 'var(--text-muted)' }}>
        <Loader2 size={32} className="animate-spin" style={{ margin: '0 auto 12px' }} />
        Loading incident #{incidentId}...
      </div>
    );
  }

  if (!incident) {
    return (
      <div style={{ textAlign: 'center', padding: '60px 0' }}>
        <h3>Incident #{incidentId} not found.</h3>
        <button className="btn btn-secondary" style={{ marginTop: '16px' }} onClick={onBack}>
          Return to Console
        </button>
      </div>
    );
  }

  const report = incident.report;
  const causes = report?.probable_causes || [];
  const questions = report?.unresolved_questions || [];
  const observations = report?.observations || [];
  const checks = report?.checks || [];
  const recoveryActions: RecoveryAction[] = incident.recovery_actions || [];

  return (
    <div>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '20px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <button className="btn btn-secondary btn-sm" onClick={onBack}>
            <ArrowLeft size={14} />
            Back
          </button>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <h2 style={{ fontSize: '1.3rem', fontWeight: 700 }}>
                Incident #{incident.id}: {incident.summary || 'Diagnostic Investigation'}
              </h2>
              <StatusBadge status={incident.status} />
            </div>
            <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
              Site: <strong>{incident.site_id}</strong> &bull; Opened {new Date(incident.created_at).toLocaleString()}
            </div>
          </div>
        </div>
      </div>

      {/* Reported Problem Statement */}
      <div className="card" style={{ borderLeft: '4px solid var(--accent-blue)' }}>
        <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: '4px' }}>
          Caller Problem Statement (Natural Language)
        </div>
        <p style={{ fontSize: '1.05rem', color: 'var(--text-primary)', fontStyle: 'italic' }}>
          "{incident.user_report}"
        </p>
      </div>

      {/* Two Column Layout: Facts & Hypotheses */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(360px, 1fr))', gap: '20px', marginBottom: '24px' }}>
        {/* Confirmed Measured Facts */}
        <div className="card">
          <div className="card-header">
            <div className="card-title">
              <CheckCircle size={16} style={{ color: 'var(--status-healthy)' }} />
              Confirmed Measured Facts
            </div>
            <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Real Probe Findings</span>
          </div>
          <ul style={{ listStyle: 'none', display: 'flex', flexDirection: 'column', gap: '8px' }}>
            {observations.length === 0 ? (
              <li style={{ color: 'var(--text-muted)', fontSize: '0.84rem' }}>No specific observations recorded.</li>
            ) : (
              observations.map((obs, i) => (
                <li key={i} style={{ fontSize: '0.84rem', display: 'flex', alignItems: 'flex-start', gap: '8px' }}>
                  <span style={{ color: 'var(--accent-blue)', marginTop: '2px' }}>&bull;</span>
                  <span>{obs}</span>
                </li>
              ))
            )}
          </ul>
        </div>

        {/* Probable Causes & Hypotheses */}
        <div className="card">
          <div className="card-header">
            <div className="card-title">
              <AlertTriangle size={16} style={{ color: 'var(--status-degraded)' }} />
              Diagnostic Hypotheses & Probable Causes
            </div>
            <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Deterministic Decision Tree</span>
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
            {causes.length === 0 ? (
              <div style={{ color: 'var(--text-muted)', fontSize: '0.84rem' }}>
                All automated tests passed; no anomalies identified.
              </div>
            ) : (
              causes.map((c, i) => (
                <div
                  key={i}
                  style={{
                    backgroundColor: 'var(--bg-card-subtle)',
                    padding: '10px 14px',
                    borderRadius: 'var(--radius-md)',
                    border: '1px solid var(--border-subtle)',
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '4px' }}>
                    <strong style={{ fontSize: '0.88rem' }}>{c.cause}</strong>
                    <span
                      style={{
                        fontSize: '0.72rem',
                        fontWeight: 700,
                        padding: '2px 6px',
                        borderRadius: 'var(--radius-sm)',
                        backgroundColor: c.confidence === 'HIGH' ? 'rgba(239, 68, 68, 0.2)' : 'rgba(245, 158, 11, 0.2)',
                        color: c.confidence === 'HIGH' ? 'var(--status-failed)' : 'var(--status-degraded)',
                      }}
                    >
                      {c.confidence} CONFIDENCE
                    </span>
                  </div>
                  <div style={{ fontSize: '0.78rem', color: 'var(--text-secondary)' }}>
                    Evidence: {c.evidence_summary}
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      </div>

      {/* Probes Matrix for this Incident */}
      <div className="card">
        <div className="card-header">
          <div className="card-title">
            <FileText size={16} />
            Diagnostic Evidence Matrix (Observed Probes)
          </div>
        </div>
        <ProbeMatrix probes={checks} />
      </div>

      {/* Unresolved Questions if any */}
      {questions.length > 0 && (
        <div className="card" style={{ borderLeft: '4px solid var(--status-degraded)' }}>
          <div className="card-header">
            <div className="card-title">
              <HelpCircle size={16} style={{ color: 'var(--status-degraded)' }} />
              Follow-Up & Unresolved Questions
            </div>
          </div>
          <ul style={{ listStyle: 'none', display: 'flex', flexDirection: 'column', gap: '6px' }}>
            {questions.map((q, i) => (
              <li key={i} style={{ fontSize: '0.84rem', color: 'var(--text-secondary)', display: 'flex', gap: '8px' }}>
                <span style={{ color: 'var(--status-degraded)' }}>?</span>
                <span>{q}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Recovery Actions & Authorized Verification Card */}
      <div className="card">
        <div className="card-header">
          <div className="card-title">
            <Wrench size={16} style={{ color: 'var(--accent-purple)' }} />
            Allowlisted Recovery Execution & Post-Action Verification
          </div>
          <div style={{ display: 'flex', gap: '8px' }}>
            <button
              className="btn btn-primary btn-sm"
              onClick={() => handleProposeAction('clear_demo_dns_fault')}
              disabled={proposing}
            >
              Propose 'Clear DNS Fault'
            </button>
            <button
              className="btn btn-secondary btn-sm"
              onClick={() => handleProposeAction('flush_dns_cache_simulated')}
              disabled={proposing}
            >
              Propose 'Flush Cache'
            </button>
          </div>
        </div>

        {recoveryActions.length === 0 ? (
          <div style={{ padding: '20px', textAlign: 'center', color: 'var(--text-muted)', fontSize: '0.86rem' }}>
            No recovery actions have been proposed yet. Click a button above to formulate an allowlisted recovery action.
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
            {recoveryActions.map((act) => (
              <div
                key={act.action_id}
                style={{
                  backgroundColor: 'var(--bg-card-subtle)',
                  border: '1px solid var(--border-color)',
                  borderRadius: 'var(--radius-md)',
                  padding: '16px',
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                    <span className="mono" style={{ fontWeight: 600 }}>{act.action_id}</span>
                    <span style={{ fontWeight: 600 }}>{act.action_type}</span>
                    <StatusBadge status={act.status} />
                  </div>
                  {act.status === 'PROPOSED' && (
                    <button
                      className="btn btn-primary btn-sm"
                      onClick={() => setActiveProposal(act)}
                    >
                      Authorize Action
                    </button>
                  )}
                </div>

                <p style={{ fontSize: '0.82rem', color: 'var(--text-secondary)', marginBottom: '8px' }}>
                  {act.impact_description}
                </p>

                {act.verification_details && (
                  <div
                    style={{
                      marginTop: '10px',
                      padding: '10px 14px',
                      borderRadius: 'var(--radius-sm)',
                      backgroundColor: act.verification_passed ? 'var(--status-healthy-bg)' : 'var(--status-failed-bg)',
                      border: `1px solid ${act.verification_passed ? 'var(--status-healthy-border)' : 'var(--status-failed-border)'}`,
                      fontSize: '0.82rem',
                    }}
                  >
                    <strong style={{ color: act.verification_passed ? 'var(--status-healthy)' : 'var(--status-failed)' }}>
                      {act.verification_passed ? 'Verified Recovery: ' : 'Verification Failed: '}
                    </strong>
                    {act.verification_details.summary}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Incident Audit Timeline */}
      <div className="card">
        <div className="card-header">
          <div className="card-title">
            <Clock size={16} />
            Incident Audit Timeline
          </div>
        </div>
        <div className="timeline">
          {incident.timeline.map((item) => (
            <div key={item.id} className="timeline-item">
              <div className="timeline-dot" />
              <div className="timeline-content">
                <div className="timeline-title">
                  <span>{item.event_type}</span>
                  <span className="timeline-time">{new Date(item.created_at).toLocaleTimeString()}</span>
                </div>
                <div className="timeline-desc">{item.description}</div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Modal for Approval & Execution */}
      {activeProposal && (
        <RecoveryModal
          actionId={activeProposal.action_id}
          incidentId={incident.id}
          actionType={activeProposal.action_type}
          impactDescription={activeProposal.impact_description}
          requiredApprovalLevel={activeProposal.required_approval_level}
          approvalToken={activeProposal.approval_token}
          tokenExpiresAt={activeProposal.token_expires_at}
          onClose={() => setActiveProposal(null)}
          onSuccess={() => {
            loadIncident();
          }}
        />
      )}
    </div>
  );
};
