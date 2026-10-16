/**
 * Typed API client for RELAY Backend.
 */
import type {
  DiagnoseResponse,
  IncidentDetail,
  OverviewStats,
  DemoStatus,
  VoiceSimulationResponse,
} from './types';

const DEFAULT_BASE_URL = 'http://localhost:8000';
const DEFAULT_API_TOKEN = 'relay-dev-token-secret-2026';

export function getApiBaseUrl(): string {
  return localStorage.getItem('relay_base_url') || DEFAULT_BASE_URL;
}

export function setApiBaseUrl(url: string): void {
  localStorage.setItem('relay_base_url', url);
}

export function getApiToken(): string {
  return localStorage.getItem('relay_api_token') || DEFAULT_API_TOKEN;
}

export function setApiToken(token: string): void {
  localStorage.setItem('relay_api_token', token);
}

async function request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const baseUrl = getApiBaseUrl();
  const token = getApiToken();

  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    Authorization: `Bearer ${token}`,
    ...(options.headers as Record<string, string> || {}),
  };

  const response = await fetch(`${baseUrl}${endpoint}`, {
    ...options,
    headers,
  });

  if (!response.ok) {
    let errorDetail = `HTTP ${response.status} ${response.statusText}`;
    try {
      const errJson = await response.json();
      if (errJson.detail) errorDetail = errJson.detail;
    } catch {
      // ignore
    }
    throw new Error(errorDetail);
  }

  return response.json() as Promise<T>;
}

export async function fetchHealth(): Promise<{ ok: boolean; service: string; version: string }> {
  const baseUrl = getApiBaseUrl();
  const res = await fetch(`${baseUrl}/health`);
  return res.json();
}

export async function fetchOverviewStats(): Promise<OverviewStats> {
  return request<OverviewStats>('/v1/overview/stats');
}

export async function fetchSites(): Promise<string[]> {
  return request<string[]>('/v1/sites');
}

export async function fetchSiteStatus(siteId: string): Promise<any> {
  return request<any>(`/v1/sites/${encodeURIComponent(siteId)}/status`);
}

export async function fetchIncidents(siteId?: string, status?: string): Promise<any[]> {
  const params = new URLSearchParams();
  if (siteId) params.append('site_id', siteId);
  if (status) params.append('status', status);
  const qs = params.toString() ? `?${params.toString()}` : '';
  return request<any[]>(`/v1/tools/incidents${qs}`);
}

export async function fetchIncidentDetail(incidentId: number): Promise<IncidentDetail> {
  return request<IncidentDetail>(`/v1/tools/incidents/${incidentId}`);
}

export async function runDiagnose(siteId: string, userReport: string): Promise<DiagnoseResponse> {
  return request<DiagnoseResponse>('/v1/tools/diagnose', {
    method: 'POST',
    body: JSON.stringify({ site_id: siteId, user_report: userReport }),
  });
}

export async function proposeRecovery(incidentId: number, actionType: string, parameters: Record<string, any> = {}): Promise<any> {
  return request<any>('/v1/tools/recovery/propose', {
    method: 'POST',
    body: JSON.stringify({ incident_id: incidentId, action_type: actionType, parameters }),
  });
}

export async function executeRecovery(actionId: string, approvalToken: string): Promise<any> {
  return request<any>('/v1/tools/recovery/execute', {
    method: 'POST',
    body: JSON.stringify({ action_id: actionId, approval_token: approvalToken }),
  });
}

export async function fetchDemoStatus(): Promise<DemoStatus> {
  return request<DemoStatus>('/v1/demo/status');
}

export async function toggleDemoFault(faultType: string, enabled: boolean): Promise<any> {
  return request<any>('/v1/demo/faults/toggle', {
    method: 'POST',
    body: JSON.stringify({ fault_type: faultType, enabled }),
  });
}

export async function clearAllDemoFaults(): Promise<any> {
  return request<any>('/v1/demo/faults/clear', {
    method: 'POST',
  });
}

export async function simulateVoice(userMessage: string, siteId: string = 'jio-lab', incidentId?: number, actionType?: string): Promise<VoiceSimulationResponse> {
  return request<VoiceSimulationResponse>('/v1/bolna/voice-simulate', {
    method: 'POST',
    body: JSON.stringify({
      user_message: userMessage,
      site_id: siteId,
      incident_id: incidentId,
      action_type: actionType,
    }),
  });
}

export async function fetchBolnaSchemas(): Promise<any> {
  return request<any>('/v1/bolna/schemas');
}
