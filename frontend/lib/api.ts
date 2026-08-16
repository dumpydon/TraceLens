import type { Evaluation, EvidenceItem, Incident, Report, Scenario } from "./types";

export interface TrafficGenerationResult {
  traffic_batch_id: string;
  started_at: string;
  ended_at: string;
  requests: number;
  results: Record<string, number>;
}

export const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, { cache: "no-store", ...init });
  if (!response.ok) {
    const payload = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(payload.detail ?? `Request failed: ${response.status}`);
  }
  return response.json();
}

export const api = {
  overview: () => request<{ active_incidents: number; resolved_incidents: number; recent_incidents: Incident[]; latest_evaluation_score: number | null }>("/api/overview"),
  incidents: () => request<Incident[]>("/api/incidents"),
  incident: (id: string) => request<Incident>(`/api/incidents/${id}`),
  createIncident: (trafficBatchId?: string) => request<Incident>("/api/incidents", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(trafficBatchId === undefined ? {} : { traffic_batch_id: trafficBatchId }) }),
  investigate: (id: string) => request(`/api/incidents/${id}/investigate`, { method: "POST" }),
  report: (id: string) => request<Report>(`/api/incidents/${id}/report`),
  evidence: (id: string) => request<EvidenceItem[]>(`/api/incidents/${id}/evidence`),
  scenarios: () => request<Scenario[]>("/api/lab/scenarios"),
  activateScenario: (name: string) => request(`/api/lab/scenarios/${name}/activate`, { method: "POST" }),
  resetLab: () => request("/api/lab/reset", { method: "POST" }),
  generateTraffic: (count = 12) => request<TrafficGenerationResult>(`/api/lab/traffic?count=${count}`, { method: "POST" }),
  labHealth: () => request<{ service: string; status: string; deployment_version?: string }[]>("/api/lab/health"),
  evaluations: () => request<Evaluation[]>("/api/evaluations"),
};
