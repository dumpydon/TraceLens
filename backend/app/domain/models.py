from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


def utc_now() -> datetime:
    return datetime.now(UTC)


class Severity(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class IncidentStatus(StrEnum):
    OPEN = "open"
    INVESTIGATING = "investigating"
    RESOLVED = "resolved"
    FAILED = "failed"


class FailureType(StrEnum):
    PAYMENT_LATENCY = "payment_latency"
    PAYMENT_FAILURE = "payment_failure"
    BAD_DEPLOYMENT = "bad_deployment"
    CONNECTION_EXHAUSTION = "connection_exhaustion"
    HEALTHY = "healthy"


class ConfidenceLevel(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class Incident(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    title: str
    service: str
    severity: Severity
    status: IncidentStatus = IncidentStatus.OPEN
    started_at: datetime = Field(default_factory=utc_now)
    scenario_label: str | None = Field(
        default=None,
        description="Operational scenario label for display; never supplied to model prompts.",
    )
    summary: str = ""
    traffic_batch_id: str | None = None
    observation_started_at: datetime | None = None
    observation_ended_at: datetime | None = None


class TrafficBatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    started_at: datetime
    ended_at: datetime
    request_count: int = Field(ge=1)
    results: dict[str, int]


class LogEntry(BaseModel):
    model_config = ConfigDict(extra="allow")

    evidence_id: str
    timestamp: datetime
    level: str
    service: str
    request_id: str
    traffic_batch_id: str | None = None
    event: str
    duration_ms: float
    status_code: int
    error_type: str | None = None
    deployment_version: str
    message: str | None = None


class Deployment(BaseModel):
    model_config = ConfigDict(extra="forbid")

    evidence_id: str
    service: str
    version: str
    deployed_at: datetime
    commit_sha: str
    summary: str


class ServiceHealth(BaseModel):
    model_config = ConfigDict(extra="forbid")

    evidence_id: str
    service: str
    status: str
    checked_at: datetime = Field(default_factory=utc_now)
    latency_ms: float
    details: str | None = None
    deployment_version: str | None = None


class RetrievedDocument(BaseModel):
    model_config = ConfigDict(extra="forbid")

    evidence_id: str
    content: str
    source: str
    document_type: str
    service: str | None = None
    failure_type: str | None = None
    relevance_score: float | None = None


class EvidenceKind(StrEnum):
    LOG = "log"
    DEPLOYMENT = "deployment"
    HEALTH = "health"
    DOCUMENT = "document"


class EvidenceItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    kind: EvidenceKind
    source: str
    summary: str
    timestamp: datetime | None = None
    details: dict[str, Any] = Field(default_factory=dict)


class RuntimeAnalysis(BaseModel):
    model_config = ConfigDict(extra="forbid")

    anomaly_summary: str
    affected_services: list[str]
    failure_signals: list[str]
    relevant_evidence_ids: list[str]
    retrieval_query: str


class Hypothesis(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str
    suspected_service: str
    suspected_failure_type: FailureType
    reasoning_summary: str
    supporting_evidence_ids: list[str]
    missing_evidence: list[str] = Field(default_factory=list)


class VerificationResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    is_sufficient: bool
    evidence_support: str
    supported_evidence_ids: list[str]
    contradicted_evidence_ids: list[str] = Field(default_factory=list)
    unresolved_questions: list[str] = Field(default_factory=list)


class EvidenceConfidence(BaseModel):
    """Deterministic evidence support score; not a calibrated probability."""

    model_config = ConfigDict(extra="forbid")

    score: int = Field(ge=0, le=100)
    level: ConfidenceLevel
    runtime_support: float = Field(ge=0, le=55)
    corroboration: float = Field(ge=0, le=25)
    verification_support: float = Field(ge=0, le=20)
    contradiction_penalty: float = Field(ge=0, le=20)
    uncertainty_penalty: float = Field(ge=0, le=15)
    supporting_request_count: int = Field(ge=0)
    total_relevant_request_count: int = Field(ge=0)
    supporting_source_types: list[str] = Field(default_factory=list)
    contradiction_count: int = Field(ge=0)
    unresolved_question_count: int = Field(ge=0)
    explanation: str


class ReportEvidence(BaseModel):
    evidence_id: str
    claim: str


class RootCauseReportDraft(BaseModel):
    """Content the report LLM may author; application metadata is intentionally absent."""

    model_config = ConfigDict(extra="forbid")

    root_cause: str
    root_cause_category: str
    affected_service: str
    summary: str
    evidence: list[ReportEvidence]
    recommended_actions: list[str]
    limitations: list[str]

    @field_validator("evidence")
    @classmethod
    def require_evidence(cls, value: list[ReportEvidence]) -> list[ReportEvidence]:
        if not value:
            raise ValueError("A root-cause report requires at least one evidence reference")
        return value


class RootCauseReport(RootCauseReportDraft):
    incident_id: str
    evidence_confidence: EvidenceConfidence | None = None
    confidence: float | None = Field(
        default=None,
        ge=0,
        le=1,
        description="Legacy model confidence retained only to load historical reports.",
    )
    generated_at: datetime = Field(default_factory=utc_now)


class InvestigationEventType(StrEnum):
    INVESTIGATION_STARTED = "investigation_started"
    CONTEXT_COLLECTION_STARTED = "context_collection_started"
    LOGS_COLLECTED = "logs_collected"
    DEPLOYMENT_FOUND = "deployment_found"
    RUNTIME_ANALYSIS_COMPLETED = "runtime_analysis_completed"
    RETRIEVAL_STARTED = "retrieval_started"
    DOCUMENTS_RETRIEVED = "documents_retrieved"
    HYPOTHESIS_GENERATED = "hypothesis_generated"
    VERIFICATION_STARTED = "verification_started"
    VERIFICATION_COMPLETED = "verification_completed"
    INVESTIGATION_REFINED = "investigation_refined"
    REPORT_GENERATED = "report_generated"
    INVESTIGATION_COMPLETED = "investigation_completed"
    INVESTIGATION_FAILED = "investigation_failed"


class InvestigationEvent(BaseModel):
    id: int | None = None
    event_type: InvestigationEventType
    timestamp: datetime = Field(default_factory=utc_now)
    incident_id: str
    stage: str
    summary: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class Scenario(BaseModel):
    name: str
    description: str
    active: bool = False
    expected_behavior: str


class EvaluationCaseResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    case_name: str
    expected_root_cause_category: str
    predicted_root_cause_category: str
    expected_affected_service: str
    predicted_affected_service: str
    expected_evidence: list[str] = Field(default_factory=list)
    retrieved_failure_types: list[str] = Field(default_factory=list)
    retrieved_evidence_ids: list[str] = Field(default_factory=list)
    citation_ids: list[str] = Field(default_factory=list)
    available_evidence_ids: list[str] = Field(default_factory=list)
    root_cause_correctness: float
    affected_service_correctness: float
    retrieval_relevance: float
    evidence_groundedness: float


class EvaluationSummary(BaseModel):
    id: str
    created_at: datetime = Field(default_factory=utc_now)
    examples: int
    root_cause_correctness: float
    affected_service_correctness: float
    retrieval_relevance: float
    evidence_groundedness: float
    case_results: list[EvaluationCaseResult] = Field(default_factory=list)
