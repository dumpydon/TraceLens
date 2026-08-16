export type IncidentStatus = "open" | "investigating" | "resolved" | "failed";

export interface Incident {
  id: string;
  title: string;
  service: string;
  severity: "low" | "medium" | "high" | "critical";
  status: IncidentStatus;
  started_at: string;
  summary: string;
}

export interface InvestigationEvent {
  id: number;
  event_type: string;
  timestamp: string;
  incident_id: string;
  stage: string;
  summary: string;
  metadata: Record<string, unknown>;
}

export interface EvidenceItem {
  id: string;
  kind: "log" | "deployment" | "health" | "document";
  source: string;
  summary: string;
  timestamp?: string;
  details: Record<string, unknown>;
}

export interface EvidenceConfidence {
  score: number;
  level: "low" | "medium" | "high";
  runtime_support: number;
  corroboration: number;
  verification_support: number;
  contradiction_penalty: number;
  uncertainty_penalty: number;
  supporting_request_count: number;
  total_relevant_request_count: number;
  supporting_source_types: string[];
  contradiction_count: number;
  unresolved_question_count: number;
  explanation: string;
}

export interface Report {
  incident_id: string;
  root_cause: string;
  root_cause_category: string;
  affected_service: string;
  summary: string;
  evidence_confidence?: EvidenceConfidence | null;
  confidence?: number | null;
  evidence: { evidence_id: string; claim: string }[];
  recommended_actions: string[];
  limitations: string[];
  generated_at: string;
}

export interface Scenario {
  name: string;
  description: string;
  expected_behavior: string;
  active: boolean;
}

export interface Evaluation {
  id: string;
  created_at: string;
  examples: number;
  root_cause_correctness: number;
  affected_service_correctness: number;
  retrieval_relevance: number;
  evidence_groundedness: number;
}
