import React, { useState } from 'react';
import { executeRecovery } from '../api';
import { ShieldAlert, CheckCircle2, AlertOctagon, Loader2 } from 'lucide-react';

interface RecoveryModalProps {
  actionId: string;
  incidentId: number;
  actionType: string;
  impactDescription: string;
  requiredApprovalLevel: string;
  approvalToken: string;
  tokenExpiresAt: string;
  onClose: () => void;
  onSuccess: (result: any) => void;
}

export const RecoveryModal: React.FC<RecoveryModalProps> = ({
  actionId,
  incidentId,
  actionType,
  impactDescription,
  requiredApprovalLevel,
  approvalToken,
  tokenExpiresAt,
  onClose,
  onSuccess,
}) => {
  const [executing, setExecuting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [executionResult, setExecutionResult] = useState<any | null>(null);

  const handleExecute = async () => {
    setExecuting(true);
    setError(null);
    try {
      const res = await executeRecovery(actionId, approvalToken);
      setExecutionResult(res);
      onSuccess(res);
    } catch (err: any) {
      setError(err.message || 'Execution failed');
    } finally {
      setExecuting(false);
    }
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <ShieldAlert size={20} style={{ color: 'var(--status-degraded)' }} />
            <h3 className="modal-title">Authorize Recovery Action</h3>
          </div>
          <button
            style={{ background: 'none', border: 'none', color: 'var(--text-muted)', cursor: 'pointer', fontSize: '1.2rem' }}
            onClick={onClose}
          >
            &times;
          </button>
        </div>

        {!executionResult ? (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
            <div
              style={{
                backgroundColor: 'rgba(245, 158, 11, 0.08)',
                border: '1px solid rgba(245, 158, 11, 0.25)',
                borderRadius: 'var(--radius-md)',
                padding: '12px 16px',
                fontSize: '0.85rem',
              }}
            >
              <div style={{ fontWeight: 600, color: 'var(--status-degraded)', marginBottom: '4px' }}>
                IMPACT ASSESSMENT
              </div>
              <p style={{ color: 'var(--text-secondary)' }}>{impactDescription}</p>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px', fontSize: '0.82rem' }}>
              <div>
                <span style={{ color: 'var(--text-muted)' }}>Action Type:</span>
                <div style={{ fontWeight: 600 }}>{actionType}</div>
              </div>
              <div>
                <span style={{ color: 'var(--text-muted)' }}>Approval Level:</span>
                <div style={{ fontWeight: 600, color: 'var(--accent-blue)' }}>{requiredApprovalLevel}</div>
              </div>
              <div>
                <span style={{ color: 'var(--text-muted)' }}>Action ID:</span>
                <div className="mono" style={{ fontSize: '0.78rem' }}>{actionId}</div>
              </div>
              <div>
                <span style={{ color: 'var(--text-muted)' }}>Target Incident:</span>
                <div style={{ fontWeight: 600 }}>#{incidentId}</div>
              </div>
            </div>

            <div>
              <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)', display: 'block', marginBottom: '4px' }}>
                Cryptographic Single-Use Approval Token:
              </span>
              <div
                className="mono"
                style={{
                  backgroundColor: 'var(--bg-input)',
                  padding: '8px 12px',
                  borderRadius: 'var(--radius-sm)',
                  fontSize: '0.75rem',
                  border: '1px solid var(--border-color)',
                  color: 'var(--text-primary)',
                  wordBreak: 'break-all',
                }}
              >
                {approvalToken}
              </div>
              <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)', marginTop: '4px', display: 'block' }}>
                Expires at: {new Date(tokenExpiresAt).toLocaleTimeString()}
              </span>
            </div>

            {error && (
              <div
                style={{
                  backgroundColor: 'var(--status-failed-bg)',
                  border: '1px solid var(--status-failed-border)',
                  color: 'var(--status-failed)',
                  padding: '10px 14px',
                  borderRadius: 'var(--radius-md)',
                  fontSize: '0.82rem',
                }}
              >
                {error}
              </div>
            )}

            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px', marginTop: '12px' }}>
              <button className="btn btn-secondary" onClick={onClose} disabled={executing}>
                Cancel
              </button>
              <button className="btn btn-primary" onClick={handleExecute} disabled={executing}>
                {executing ? (
                  <>
                    <Loader2 size={16} className="animate-spin" />
                    Executing & Verifying...
                  </>
                ) : (
                  'Authorize & Execute'
                )}
              </button>
            </div>
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '16px', textAlign: 'center', padding: '16px 0' }}>
            {executionResult.verification_passed ? (
              <>
                <CheckCircle2 size={48} style={{ color: 'var(--status-healthy)', margin: '0 auto' }} />
                <h4 style={{ fontSize: '1.2rem', fontWeight: 700, color: 'var(--status-healthy)' }}>
                  Verified Recovery Confirmed
                </h4>
                <p style={{ fontSize: '0.86rem', color: 'var(--text-secondary)' }}>
                  {executionResult.verification_details?.summary || executionResult.message}
                </p>
              </>
            ) : (
              <>
                <AlertOctagon size={48} style={{ color: 'var(--status-failed)', margin: '0 auto' }} />
                <h4 style={{ fontSize: '1.2rem', fontWeight: 700, color: 'var(--status-failed)' }}>
                  Post-Action Verification Failed
                </h4>
                <p style={{ fontSize: '0.86rem', color: 'var(--status-failed)' }}>
                  {executionResult.verification_details?.summary || 'Checks are still failing after execution.'}
                </p>
                <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                  RELAY will not falsely report resolution.
                </div>
              </>
            )}

            <button className="btn btn-primary" style={{ marginTop: '16px' }} onClick={onClose}>
              Done
            </button>
          </div>
        )}
      </div>
    </div>
  );
};
