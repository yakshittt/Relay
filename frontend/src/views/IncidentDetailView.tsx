import React, { useState, useEffect, useRef } from 'react';
import { fetchIncidentDetail, proposeRecovery, interpretIncident } from '../api';
import type { IncidentDetail, RecoveryAction, AIInterpretationResponse } from '../types';
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
  Sparkles,
  RefreshCw,
  Send,
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

  // AI Interpretation State (Milestone 2)
  const [aiInterpretation, setAiInterpretation] = useState<AIInterpretationResponse | null>(null);
  const [aiLoading, setAiLoading] = useState(false);
  const [aiQuerying, setAiQuerying] = useState(false);
  const [aiError, setAiError] = useState<string | null>(null);
  const [userQuery, setUserQuery] = useState('');
  const [activeQuery, setActiveQuery] = useState<string | null>(null);
  const [pendingQuery, setPendingQuery] = useState<string | null>(null);
  const abortControllerRef = useRef<AbortController | null>(null);
  const currentIncidentIdRef = useRef<number>(incidentId);

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
    currentIncidentIdRef.current = incidentId;
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }
    setAiInterpretation(null);
    setAiLoading(false);
    setAiQuerying(false);
    setAiError(null);
    setUserQuery('');
    setActiveQuery(null);
    setPendingQuery(null);

    loadIncident();

    return () => {
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
    };
  }, [incidentId]);

  const handleGenerateInterpretation = async (query?: string) => {
    if (aiLoading || aiQuerying) return; // Prevent duplicate simultaneous submissions

    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
    const controller = new AbortController();
    abortControllerRef.current = controller;

    const trimmedQuery = query?.trim();
    const isFollowUp = Boolean(trimmedQuery);

    if (isFollowUp) {
      setAiQuerying(true);
      setPendingQuery(trimmedQuery || null);
    } else {
      setAiLoading(true);
    }
    setAiError(null);
    const targetIncidentId = incidentId;

    try {
      const data = await interpretIncident(targetIncidentId, trimmedQuery, controller.signal);
      // Guard against stale response if user switched incident in flight
      if (currentIncidentIdRef.current === targetIncidentId) {
        setAiInterpretation(data);
        if (isFollowUp && trimmedQuery) {
          setActiveQuery(trimmedQuery);
          setUserQuery(''); // Clear query input after successful submission
          setPendingQuery(null);
        }
      }
    } catch (err: any) {
      if (err.name === 'AbortError') {
        return;
      }
      if (currentIncidentIdRef.current === targetIncidentId) {
        setAiError(err.message || 'Failed to generate AI incident interpretation.');
      }
    } finally {
      if (currentIncidentIdRef.current === targetIncidentId) {
        setAiLoading(false);
        setAiQuerying(false);
      }
    }
  };

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

      {/* AI Incident Interpretation Card (Milestone 2) */}
      <div className="card" style={{ border: '1px solid var(--border-color)', backgroundColor: 'var(--bg-card)' }}>
        <div className="card-header">
          <div className="card-title">
            <Sparkles size={18} style={{ color: 'var(--accent-purple)' }} />
            <span>AI Incident Interpretation</span>
            {aiInterpretation && (
              <span
                className="badge"
                style={{
                  backgroundColor: 'rgba(99, 102, 241, 0.15)',
                  color: 'var(--accent-indigo)',
                  border: '1px solid rgba(99, 102, 241, 0.3)',
                  fontFamily: 'var(--font-mono)',
                  fontSize: '0.72rem',
                  marginLeft: '6px',
                }}
              >
                {aiInterpretation.provider_used}
              </span>
            )}
          </div>
          {aiInterpretation && (
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                Generated {new Date(aiInterpretation.generated_at).toLocaleTimeString()}
              </span>
              <button
                className="btn btn-secondary btn-sm"
                onClick={() => handleGenerateInterpretation(activeQuery || undefined)}
                disabled={aiLoading || aiQuerying}
                title="Refresh Interpretation"
              >
                <RefreshCw size={13} className={aiLoading || aiQuerying ? 'animate-spin' : ''} />
                Refresh
              </button>
            </div>
          )}
        </div>

        {/* Initial State (Explicit Generate button) */}
        {!aiInterpretation && !aiLoading && !aiError && (
          <div style={{ padding: '24px', textAlign: 'center' }}>
            <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem', marginBottom: '16px' }}>
              Generate an evidence-grounded, plain-language synthesis of this incident based on server-verified probes and hardware sentinels.
            </p>
            <button
              className="btn btn-primary"
              onClick={() => handleGenerateInterpretation()}
              disabled={aiLoading || aiQuerying}
            >
              <Sparkles size={15} />
              Generate Interpretation
            </button>
          </div>
        )}

        {/* Loading State for initial synthesis */}
        {aiLoading && !aiInterpretation && (
          <div style={{ padding: '32px 16px', textAlign: 'center', color: 'var(--text-muted)' }}>
            <Loader2 size={24} className="animate-spin" style={{ margin: '0 auto 10px', color: 'var(--accent-blue)' }} />
            <div style={{ fontSize: '0.88rem' }}>Synthesizing server diagnostic evidence...</div>
          </div>
        )}

        {/* Error State with Retry */}
        {aiError && !aiLoading && !aiQuerying && (
          <div
            style={{
              padding: '16px',
              backgroundColor: 'var(--status-failed-bg)',
              border: '1px solid var(--status-failed-border)',
              borderRadius: 'var(--radius-md)',
              marginBottom: aiInterpretation ? '16px' : '0',
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '8px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: 'var(--status-failed)' }}>
                <AlertTriangle size={16} />
                <span style={{ fontSize: '0.86rem', fontWeight: 600 }}>Interpretation Error: {aiError}</span>
              </div>
              <button
                className="btn btn-secondary btn-sm"
                onClick={() => handleGenerateInterpretation(pendingQuery || userQuery || activeQuery || undefined)}
                disabled={aiLoading || aiQuerying}
              >
                <RefreshCw size={13} />
                Retry
              </button>
            </div>
          </div>
        )}

        {/* Rendered Interpretation */}
        {aiInterpretation && (
          <div>
            {/* Follow-up Query Processing Indicator */}
            {aiQuerying && (
              <div
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '8px',
                  padding: '8px 12px',
                  backgroundColor: 'rgba(59, 130, 246, 0.08)',
                  border: '1px solid rgba(59, 130, 246, 0.25)',
                  borderRadius: 'var(--radius-md)',
                  marginBottom: '14px',
                  fontSize: '0.84rem',
                  color: 'var(--accent-blue)',
                }}
              >
                <Loader2 size={15} className="animate-spin" style={{ flexShrink: 0 }} />
                <span>
                  Processing follow-up query: <strong>"{pendingQuery}"</strong>...
                </span>
              </div>
            )}

            {/* Active Follow-up Query Banner */}
            {activeQuery && !aiQuerying && (
              <div
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  gap: '8px',
                  padding: '8px 12px',
                  backgroundColor: 'rgba(99, 102, 241, 0.08)',
                  border: '1px solid rgba(99, 102, 241, 0.25)',
                  borderRadius: 'var(--radius-md)',
                  marginBottom: '16px',
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <HelpCircle size={15} style={{ color: 'var(--accent-indigo)', flexShrink: 0 }} />
                  <span style={{ fontSize: '0.84rem', color: 'var(--text-secondary)' }}>
                    Follow-up query: <strong style={{ color: 'var(--text-primary)' }}>"{activeQuery}"</strong>
                  </span>
                </div>
                <span
                  style={{
                    fontSize: '0.72rem',
                    backgroundColor: 'rgba(99, 102, 241, 0.15)',
                    color: 'var(--accent-indigo)',
                    padding: '2px 6px',
                    borderRadius: 'var(--radius-sm)',
                    fontWeight: 600,
                  }}
                >
                  Answered
                </span>
              </div>
            )}

            {/* Deterministic Fallback Alert */}
            {aiInterpretation.fallback_used && (
              <div
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '10px',
                  padding: '10px 14px',
                  backgroundColor: 'var(--status-degraded-bg)',
                  border: '1px solid var(--status-degraded-border)',
                  borderRadius: 'var(--radius-md)',
                  marginBottom: '16px',
                  fontSize: '0.84rem',
                  color: 'var(--status-degraded)',
                }}
              >
                <AlertTriangle size={16} style={{ flexShrink: 0 }} />
                <span>
                  <strong>Deterministic Fallback Engaged:</strong> Upstream LLM provider was unavailable or diagnostic evidence was partial; displaying rule-based synthesis.
                </span>
              </div>
            )}

            {/* Summary Narrative */}
            <div style={{ marginBottom: '18px' }}>
              <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: '6px' }}>
                Incident Summary
              </div>
              <p style={{ fontSize: '0.98rem', color: 'var(--text-primary)', lineHeight: 1.55 }}>
                {aiInterpretation.interpretation.summary}
              </p>
            </div>

            {/* Grounded Facts List */}
            <div style={{ marginBottom: '18px' }}>
              <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: '8px' }}>
                Server-Grounded Facts & Citations
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                {aiInterpretation.interpretation.grounded_facts.map((fact, idx) => {
                  const isUnverified = fact.source === 'unverified_model_claim';
                  return (
                    <div
                      key={idx}
                      style={{
                        display: 'flex',
                        alignItems: 'flex-start',
                        gap: '10px',
                        padding: '8px 12px',
                        backgroundColor: 'var(--bg-card-subtle)',
                        borderRadius: 'var(--radius-sm)',
                        border: isUnverified ? '1px solid var(--status-failed-border)' : '1px solid var(--border-subtle)',
                      }}
                    >
                      {isUnverified ? (
                        <span
                          style={{
                            backgroundColor: 'var(--status-failed-bg)',
                            color: 'var(--status-failed)',
                            border: '1px solid var(--status-failed-border)',
                            fontSize: '0.72rem',
                            fontWeight: 700,
                            padding: '2px 6px',
                            borderRadius: 'var(--radius-sm)',
                            whiteSpace: 'nowrap',
                            flexShrink: 0,
                          }}
                        >
                          UNVERIFIED CLAIM
                        </span>
                      ) : (
                        <span
                          style={{
                            backgroundColor: fact.source.startsWith('device:')
                              ? 'rgba(139, 92, 246, 0.15)'
                              : 'rgba(59, 130, 246, 0.15)',
                            color: fact.source.startsWith('device:') ? 'var(--accent-purple)' : 'var(--accent-blue)',
                            border: `1px solid ${
                              fact.source.startsWith('device:')
                                ? 'rgba(139, 92, 246, 0.3)'
                                : 'rgba(59, 130, 246, 0.3)'
                            }`,
                            fontSize: '0.72rem',
                            fontFamily: 'var(--font-mono)',
                            fontWeight: 600,
                            padding: '2px 6px',
                            borderRadius: 'var(--radius-sm)',
                            whiteSpace: 'nowrap',
                            flexShrink: 0,
                          }}
                        >
                          {fact.source}
                        </span>
                      )}
                      <span
                        style={{
                          fontSize: '0.84rem',
                          color: isUnverified ? 'var(--status-failed)' : 'var(--text-secondary)',
                          fontStyle: isUnverified ? 'italic' : 'normal',
                        }}
                      >
                        {fact.statement}
                      </span>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Diagnostic Hypothesis & Confidence */}
            <div
              style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))',
                gap: '14px',
                marginBottom: '18px',
              }}
            >
              <div
                style={{
                  padding: '12px 14px',
                  backgroundColor: 'var(--bg-card-subtle)',
                  borderRadius: 'var(--radius-md)',
                  border: '1px solid var(--border-subtle)',
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
                  <span style={{ fontSize: '0.78rem', color: 'var(--text-muted)', textTransform: 'uppercase' }}>
                    Root Cause Hypothesis
                  </span>
                  <span
                    style={{
                      fontSize: '0.72rem',
                      fontWeight: 700,
                      padding: '2px 6px',
                      borderRadius: 'var(--radius-sm)',
                      backgroundColor:
                        aiInterpretation.interpretation.confidence === 'HIGH'
                          ? 'rgba(239, 68, 68, 0.2)'
                          : 'rgba(245, 158, 11, 0.2)',
                      color:
                        aiInterpretation.interpretation.confidence === 'HIGH'
                          ? 'var(--status-failed)'
                          : 'var(--status-degraded)',
                    }}
                  >
                    {aiInterpretation.interpretation.confidence} CONFIDENCE
                  </span>
                </div>
                <div style={{ fontSize: '0.88rem', color: 'var(--text-primary)', fontWeight: 500 }}>
                  {aiInterpretation.interpretation.diagnostic_hypothesis}
                </div>
              </div>

              <div
                style={{
                  padding: '12px 14px',
                  backgroundColor: 'var(--bg-card-subtle)',
                  borderRadius: 'var(--radius-md)',
                  border: '1px solid var(--border-subtle)',
                }}
              >
                <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: '6px' }}>
                  Recommended Next Step
                </div>
                <div style={{ fontSize: '0.88rem', color: 'var(--text-primary)', fontWeight: 500 }}>
                  {aiInterpretation.interpretation.recommended_action}
                </div>
                <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '6px', fontStyle: 'italic' }}>
                  Note: All recoveries require approval-token verification below.
                </div>
              </div>
            </div>

            {/* Uncertainty Caveats if any */}
            {aiInterpretation.interpretation.uncertainty_caveats &&
              aiInterpretation.interpretation.uncertainty_caveats.length > 0 && (
                <div style={{ marginBottom: '18px' }}>
                  <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: '6px' }}>
                    Telemetry Gaps & Uncertainty Caveats
                  </div>
                  <ul style={{ listStyle: 'none', display: 'flex', flexDirection: 'column', gap: '4px' }}>
                    {aiInterpretation.interpretation.uncertainty_caveats.map((c, i) => (
                      <li key={i} style={{ fontSize: '0.82rem', color: 'var(--text-secondary)', display: 'flex', gap: '8px' }}>
                        <span style={{ color: 'var(--status-degraded)' }}>&bull;</span>
                        <span>{c}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}

            {/* Ask AI Follow-up Input */}
            <form
              onSubmit={(e) => {
                e.preventDefault();
                const trimmed = userQuery.trim();
                if (!trimmed || aiLoading || aiQuerying) return;
                handleGenerateInterpretation(trimmed);
              }}
              style={{
                display: 'flex',
                gap: '8px',
                marginTop: '12px',
                paddingTop: '14px',
                borderTop: '1px solid var(--border-subtle)',
              }}
            >
              <input
                type="text"
                className="input"
                placeholder="Ask AI follow-up question or request clarification..."
                value={userQuery}
                onChange={(e) => setUserQuery(e.target.value)}
                disabled={aiLoading || aiQuerying}
                style={{ flex: 1 }}
              />
              <button
                type="submit"
                className="btn btn-primary"
                disabled={aiLoading || aiQuerying || !userQuery.trim()}
              >
                {aiQuerying ? (
                  <>
                    <Loader2 size={14} className="animate-spin" />
                    Asking...
                  </>
                ) : (
                  <>
                    <Send size={14} />
                    Ask AI
                  </>
                )}
              </button>
            </form>
          </div>
        )}
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
