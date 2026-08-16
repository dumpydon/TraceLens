from datetime import UTC, datetime, timedelta

import pytest
from pydantic import ValidationError

from app.domain.models import (
    Deployment,
    EvidenceItem,
    EvidenceKind,
    FailureType,
    Hypothesis,
    Incident,
    LogEntry,
    ServiceHealth,
    VerificationResult,
)
from app.graph.nodes import InvestigationNodes
from app.graph.state import initial_state


def runtime_log(
    evidence_id: str,
    request_id: str,
    service: str,
    duration_ms: float,
    status_code: int,
    error_type: str | None,
) -> LogEntry:
    return LogEntry(
        evidence_id=evidence_id,
        timestamp=datetime(2026, 8, 15, 10, 0, tzinfo=UTC),
        level="ERROR" if status_code >= 500 else "INFO",
        service=service,
        request_id=request_id,
        event="request.failed" if status_code >= 500 else "request.completed",
        duration_ms=duration_ms,
        status_code=status_code,
        error_type=error_type,
        deployment_version="test",
    )


def payment_latency_logs() -> list[LogEntry]:
    logs = []
    for index in range(2):
        request_id = f"latency-{index}"
        logs.extend(
            [
                runtime_log(
                    f"log:checkout:{index}",
                    request_id,
                    "checkout-service",
                    1015,
                    504,
                    "UpstreamPaymentTimeout",
                ),
                runtime_log(
                    f"log:payment:{index}",
                    request_id,
                    "payment-service",
                    1800,
                    200,
                    None,
                ),
            ]
        )
    return logs


def test_evidence_id_resolution_rejects_unknown_ids():
    evidence = [EvidenceItem(id="log:payment:1", kind=EvidenceKind.LOG, source="payment", summary="failed")]
    valid, invalid = InvestigationNodes._resolve_ids(["log:payment:1", "log:invented:9"], evidence)
    assert valid == ["log:payment:1"]
    assert invalid == ["log:invented:9"]


def test_verification_rejects_citations_that_do_not_support_hypothesis():
    state = initial_state("INC-1")
    state["active_hypothesis"] = Hypothesis(
        title="Connections exhausted",
        suspected_service="payment-service",
        suspected_failure_type="connection_exhaustion",
        reasoning_summary="Candidate",
        supporting_evidence_ids=["log:checkout:1", "log:payment:1"],
    )
    state["evidence"] = [
        EvidenceItem(
            id="log:checkout:1",
            kind=EvidenceKind.LOG,
            source="checkout-service",
            summary="timeout",
            details={
                "request_id": "req-1",
                "status_code": 504,
                "duration_ms": 1000,
                "error_type": "UpstreamPaymentTimeout",
            },
        ),
        EvidenceItem(
            id="log:payment:1",
            kind=EvidenceKind.LOG,
            source="payment-service",
            summary="slow completion",
            details={
                "request_id": "req-1",
                "status_code": 200,
                "duration_ms": 1800,
                "error_type": None,
            },
        ),
    ]
    result = InvestigationNodes._fallback_verification(state)
    assert result.is_sufficient is False
    assert result.supported_evidence_ids == []
    assert result.evidence_support.startswith("Evidence is insufficient")


def test_hypothesis_structured_schema_allows_only_canonical_failure_types():
    schema = Hypothesis.model_json_schema()
    assert set(schema["$defs"]["FailureType"]["enum"]) == {
        "payment_latency",
        "payment_failure",
        "bad_deployment",
        "connection_exhaustion",
        "healthy",
    }

    with pytest.raises(ValidationError):
        Hypothesis(
            title="Unsupported diagnosis",
            suspected_service="checkout-service",
            suspected_failure_type="timeout handling regression",
            reasoning_summary="Unsupported",
            supporting_evidence_ids=[],
        )


def test_payment_latency_pattern_wins_despite_healthy_service_check():
    state = initial_state("INC-LATENCY")
    state["logs"] = payment_latency_logs()
    state["service_health"] = [
        ServiceHealth(
            evidence_id="health:payment:1",
            service="payment-service",
            status="healthy",
            latency_ms=2,
            details="available_connections=100",
        )
    ]

    hypothesis = InvestigationNodes._fallback_hypothesis(state)

    assert hypothesis.suspected_failure_type == FailureType.PAYMENT_LATENCY
    assert hypothesis.suspected_service == "payment-service"


def test_timeout_handling_deployment_metadata_does_not_establish_bad_deployment():
    state = initial_state("INC-DEPLOYMENT-CONTEXT")
    state["logs"] = payment_latency_logs()
    state["deployments"] = [
        Deployment(
            evidence_id="deployment:checkout-service:1.3.0",
            service="checkout-service",
            version="1.3.0",
            deployed_at=datetime.now(UTC) - timedelta(days=3),
            commit_sha="a91c2f7",
            summary="Checkout request correlation and timeout handling",
        )
    ]

    hypothesis = InvestigationNodes._fallback_hypothesis(state)

    assert hypothesis.suspected_failure_type == FailureType.PAYMENT_LATENCY
    assert hypothesis.suspected_failure_type != FailureType.BAD_DEPLOYMENT


async def test_unknown_legacy_failure_type_terminates_with_safe_unverified_report(
    settings, database
):
    incident = Incident(
        id="INC-LEGACY",
        title="Legacy checkpoint",
        service="checkout-service",
        severity="high",
    )
    database.create_incident(incident)
    state = initial_state(incident.id, max_iterations=3)
    state["iteration_count"] = 3
    state["evidence"] = [
        EvidenceItem(
            id="log:checkout:1",
            kind=EvidenceKind.LOG,
            source="checkout-service",
            summary="Checkout returned 504 after one second",
            details={"request_id": "req-1", "status_code": 504, "duration_ms": 1015},
        )
    ]
    state["active_hypothesis"] = Hypothesis.model_construct(
        title="Checkout timeout regression",
        suspected_service="checkout-service",
        suspected_failure_type="timeout handling regression",
        reasoning_summary="Legacy checkpoint hypothesis",
        supporting_evidence_ids=["log:checkout:1"],
        confidence=0.95,
        missing_evidence=[],
    )
    state["verification"] = VerificationResult(
        is_sufficient=False,
        evidence_support="Evidence is insufficient",
        supported_evidence_ids=[],
    )

    result = await InvestigationNodes(database, settings).generate_report(state)
    report = result["final_report"]

    assert report.root_cause.startswith("Unverified hypothesis:")
    assert report.root_cause_category == "timeout handling regression"
    assert report.evidence_confidence.score == 0
    assert report.evidence_confidence.level.value == "low"
    assert any("not a supported V1 category" in item for item in report.limitations)
    assert any("insufficient" in item.lower() for item in report.limitations)
    assert database.get_incident(incident.id).status.value == "resolved"
    assert database.get_report(incident.id) is not None


async def test_llm_verification_cannot_be_sufficient_without_category_runtime_support(
    settings, database
):
    class UnsupportedVerifier:
        enabled = True

        async def invoke(self, *_args, **_kwargs):
            return VerificationResult(
                is_sufficient=True,
                evidence_support="The hypothesis is strongly supported.",
                supported_evidence_ids=["health:payment:1"],
            )

    state = initial_state("INC-STRICT-VERIFY")
    database.create_incident(
        Incident(
            id=state["incident_id"],
            title="Strict verification",
            service="payment-service",
            severity="high",
        )
    )
    state["active_hypothesis"] = Hypothesis(
        title="Payment latency",
        suspected_service="payment-service",
        suspected_failure_type=FailureType.PAYMENT_LATENCY,
        reasoning_summary="Candidate",
        supporting_evidence_ids=["health:payment:1"],
    )
    state["evidence"] = [
        EvidenceItem(
            id="health:payment:1",
            kind=EvidenceKind.HEALTH,
            source="payment-service",
            summary="Payment health is healthy",
            details={"status": "healthy"},
        )
    ]
    nodes = InvestigationNodes(database, settings)
    nodes.reasoner = UnsupportedVerifier()

    result = await nodes.verify_hypothesis(state)
    verification = result["verification"]

    assert verification.is_sufficient is False
    assert verification.supported_evidence_ids == []
    assert verification.evidence_support.startswith("Evidence is insufficient")
    assert "strongly supported" not in verification.evidence_support
    assert result["evidence_confidence"].level.value == "low"
    assert result["evidence_confidence"].score <= 54
