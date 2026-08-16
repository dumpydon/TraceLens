from __future__ import annotations

from typing import TypedDict

from app.domain.models import (
    Deployment,
    EvidenceConfidence,
    EvidenceItem,
    Hypothesis,
    Incident,
    LogEntry,
    RetrievedDocument,
    RootCauseReport,
    RuntimeAnalysis,
    ServiceHealth,
    VerificationResult,
)


class InvestigationState(TypedDict):
    incident_id: str
    incident: Incident | None
    logs: list[LogEntry]
    deployments: list[Deployment]
    service_health: list[ServiceHealth]
    runtime_analysis: RuntimeAnalysis | None
    retrieval_query: str
    retrieved_documents: list[RetrievedDocument]
    hypotheses: list[Hypothesis]
    active_hypothesis: Hypothesis | None
    evidence: list[EvidenceItem]
    verification: VerificationResult | None
    evidence_confidence: EvidenceConfidence | None
    iteration_count: int
    max_iterations: int
    final_report: RootCauseReport | None
    errors: list[str]


def initial_state(incident_id: str, max_iterations: int = 3) -> InvestigationState:
    return InvestigationState(
        incident_id=incident_id,
        incident=None,
        logs=[],
        deployments=[],
        service_health=[],
        runtime_analysis=None,
        retrieval_query="",
        retrieved_documents=[],
        hypotheses=[],
        active_hypothesis=None,
        evidence=[],
        verification=None,
        evidence_confidence=None,
        iteration_count=0,
        max_iterations=max_iterations,
        final_report=None,
        errors=[],
    )
