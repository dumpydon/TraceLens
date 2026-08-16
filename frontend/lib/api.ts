import type { Evaluation, EvidenceItem, Incident, Report, Scenario } from "./types";

export interface TrafficGenerationResult {
  traffic_batch_id: string;
  started_at: string;
  ended_at: string;
  requests: number;
  results: Record<string, number>;
}

export const API_BASE = (
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000"
).replace(/\/$/, "");
export const BACKEND_WAKE_MESSAGE =
  "TraceLens backend is waking up. This can take up to a minute on the demo environment. Please retry shortly.";

class ApiResponseError extends Error {}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  try {
    const response = await fetch(`${API_BASE}${path}`, { cache: "no-store", ...init });
    if (!response.ok) {
      if ([502, 503, 504].includes(response.status)) {
        throw new Error(BACKEND_WAKE_MESSAGE);
      }
      const payload = await response.json().catch(() => ({ detail: response.statusText }));
      throw new ApiResponseError(payload.detail ?? `Request failed: ${response.status}`);
    }
    return await response.json();
  } catch (error) {
    if (error instanceof ApiResponseError || (error instanceof Error && error.message === BACKEND_WAKE_MESSAGE)) {
      throw error;
    }
    throw new Error(BACKEND_WAKE_MESSAGE);
  }
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
