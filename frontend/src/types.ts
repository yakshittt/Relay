/**
 * Frontend TypeScript data models matching RELAY backend schemas.
 */

export type HealthStatus = 'healthy' | 'degraded' | 'failed' | 'unknown';
export type ProbeStatus = 'HEALTHY' | 'DEGRADED' | 'FAILED' | 'UNKNOWN';
export type ActionStatus = 'PROPOSED' | 'APPROVED' | 'EXECUTING' | 'SUCCEEDED' | 'FAILED' | 'REJECTED';

export interface ProbeResult {
  name: string;
  target: string;
  status: ProbeStatus;
  ok: boolean;
  latency_ms: number;
  detail: string;
  evidence: Record<string, any>;
  error_category?: string | null;
  timestamp: string;
  is_simulated: boolean;
}

export interface ProbableCause {
  cause: string;
  confidence: 'HIGH' | 'MEDIUM' | 'LOW';
  evidence_summary: string;
}

export interface DeviceHeartbeatView {
  device_id: string;
  site_id: string;
  received_at: string;
  wifi_rssi_dbm?: number | null;
  uptime_seconds?: number | null;
  firmware_version?: string | null;
  free_heap?: number | null;
  cycle_count?: number | null;
  age_seconds?: number | null;
  online: boolean;
  status: 'ONLINE' | 'STALE' | 'UNKNOWN';
}

export interface DiagnosisReport {
  site_id: string;
  observed_at: string;
  status: HealthStatus;
  summary: string;
  diagnosis: string;
  observations: string[];
  checks: ProbeResult[];
  probable_causes: ProbableCause[];
  unresolved_questions: string[];
  recommended_next_step: string;
  devices: DeviceHeartbeatView[];
  demo_dns_fault_active: boolean;
  demo_mode_active: boolean;
}

export interface DiagnoseResponse extends DiagnosisReport {
  incident_id: number;
}

export interface TimelineItem {
  id: number;
  incident_id: number;
  event_type: string;
  description: string;
  metadata: Record<string, any>;
  created_at: string;
}

export interface RecoveryAction {
  id: string;
  action_id: string;
  incident_id: number;
  action_type: string;
  parameters: Record<string, any>;
  impact_description: string;
  required_approval_level: string;
  status: ActionStatus;
  idempotency_key?: string | null;
  approval_token: string;
  token_expires_at: string;
  is_consumed: boolean;
  outcome?: string | null;
  verification_passed?: boolean | null;
  verification_details?: Record<string, any> | null;
  created_at: string;
  executed_at?: string | null;
}

export interface IncidentDetail {
  id: number;
  site_id: string;
  created_at: string;
  updated_at: string;
  status: HealthStatus | string;
  user_report: string;
  summary: string;
  diagnosis: string;
  report: DiagnosisReport;
  timeline: TimelineItem[];
  recovery_actions: RecoveryAction[];
}

export interface OverviewStats {
  total_sites: number;
  open_incidents: number;
  total_incidents: number;
  online_devices: number;
  stale_devices: number;
  recovery_success_rate: number;
  total_recovery_actions: number;
}

export interface DemoStatus {
  demo_mode: boolean;
  active_faults: {
    dns_outage: boolean;
    business_http_503: boolean;
    stale_heartbeat: boolean;
    gateway_loss: boolean;
  };
}

export interface VoiceSimulationResponse {
  intent: string;
  spoken_response: string;
  tool_call: {
    name: string;
    parameters: Record<string, any>;
    result: any;
  };
  incident_id?: number;
  voice_details?: any;
}

export interface GroundedFact {
  source: string;
  statement: string;
}

export interface AIInterpretation {
  summary: string;
  grounded_facts: GroundedFact[];
  diagnostic_hypothesis: string;
  confidence: 'HIGH' | 'MEDIUM' | 'LOW';
  recommended_action: string;
  uncertainty_caveats: string[];
}

export interface AIInterpretationResponse {
  incident_id: number;
  site_id: string;
  status: string;
  interpretation: AIInterpretation;
  fallback_used: boolean;
  provider_used: string;
  generated_at: string;
}

