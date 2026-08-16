from datetime import UTC, datetime, timedelta

from app.domain.models import (
    ConfidenceLevel,
    Deployment,
    FailureType,
    Hypothesis,
    Incident,
    LogEntry,
    RetrievedDocument,
    RootCauseReportDraft,
    ServiceHealth,
    VerificationResult,
)
from app.services.evidence_confidence import calculate_evidence_confidence, confidence_level

NOW = datetime(2026, 8, 15, 10, 0, tzinfo=UTC)


def log(
    evidence_id: str,
    request_id: str,
    service: str,
    duration_ms: float,
    status_code: int,
    error_type: str | None = None,
) -> LogEntry:
    return LogEntry(
        evidence_id=evidence_id,
        timestamp=NOW,
        level="ERROR" if status_code >= 500 else "INFO",
        service=service,
        request_id=request_id,
        event="request.failed" if status_code >= 500 else "request.completed",
        duration_ms=duration_ms,
        status_code=status_code,
        error_type=error_type,
        deployment_version="test",
    )


def hypothesis(
    category: FailureType,
    *,
    title: str = "Supported diagnosis",
    missing_evidence: list[str] | None = None,
) -> Hypothesis:
    return Hypothesis(
        title=title,
        suspected_service="payment-service" if category != FailureType.HEALTHY else "none",
        suspected_failure_type=category,
        reasoning_summary="Runtime evidence supports the canonical pattern.",
        supporting_evidence_ids=[],
        missing_evidence=missing_evidence or [],
    )


def verification(
    sufficient: bool = True,
    *,
    contradicted: list[str] | None = None,
    unresolved: list[str] | None = None,
) -> VerificationResult:
    return VerificationResult(
        is_sufficient=sufficient,
        evidence_support="Supported" if sufficient else "Insufficient",
        supported_evidence_ids=[],
        contradicted_evidence_ids=contradicted or [],
        unresolved_questions=unresolved or [],
    )


def payment_health(
    status: str = "healthy", details: str = "available_connections=100"
) -> list[ServiceHealth]:
    return [
        ServiceHealth(
            evidence_id="health:payment",
            service="payment-service",
            status=status,
            checked_at=NOW,
            latency_ms=2,
            details=details,
        )
    ]


def document(category: FailureType, document_type: str = "runbook") -> RetrievedDocument:
    return RetrievedDocument(
        evidence_id=f"doc:{category.value}:{document_type}",
        content="Operational interpretation for the matching runtime pattern.",
        source=f"{document_type}.md",
        document_type=document_type,
        service="payment-service",
        failure_type=category.value,
    )


def latency_logs(count: int = 6) -> list[LogEntry]:
    result = []
    for index in range(count):
        request_id = f"latency-{index}"
        result.extend(
            [
                log(
                    f"checkout:{index}",
                    request_id,
                    "checkout-service",
                    1015,
                    504,
                    "UpstreamPaymentTimeout",
                ),
                log(f"payment:{index}", request_id, "payment-service", 1800, 200),
            ]
        )
    return result


def score(
    category: FailureType,
    logs: list[LogEntry],
    *,
    verified: VerificationResult | None = None,
    health: list[ServiceHealth] | None = None,
    documents: list[RetrievedDocument] | None = None,
    deployments: list[Deployment] | None = None,
    selected_hypothesis: Hypothesis | None = None,
):
    return calculate_evidence_confidence(
        hypothesis=selected_hypothesis or hypothesis(category),
        verification=verified or verification(),
        logs=logs,
        service_health=health or [],
        deployments=deployments or [],
        retrieved_documents=documents or [],
        incident=Incident(
            id="INC-CONFIDENCE",
            title="Confidence fixture",
            service="checkout-service",
            severity="high",
            started_at=NOW,
        ),
    )


def test_strong_payment_latency_is_high():
    result = score(
        FailureType.PAYMENT_LATENCY,
        latency_logs(),
        health=payment_health(),
        documents=[document(FailureType.PAYMENT_LATENCY)],
    )

    assert result.level == ConfidenceLevel.HIGH
    assert 80 <= result.score <= 100
    assert result.supporting_request_count == 6
    assert result.total_relevant_request_count == 6


def test_incomplete_payment_latency_scores_below_fully_correlated_evidence():
    complete = score(
        FailureType.PAYMENT_LATENCY,
        latency_logs(),
        health=payment_health(),
        documents=[document(FailureType.PAYMENT_LATENCY)],
    )
    incomplete_logs = [
        log(
            "checkout:one",
            "latency-one",
            "checkout-service",
            1015,
            504,
            "UpstreamPaymentTimeout",
        )
    ]
    incomplete = score(
        FailureType.PAYMENT_LATENCY,
        incomplete_logs,
        verified=verification(False, unresolved=["Where is the paired payment completion?"]),
        health=payment_health(),
        documents=[document(FailureType.PAYMENT_LATENCY)],
        selected_hypothesis=hypothesis(
            FailureType.PAYMENT_LATENCY,
            missing_evidence=["Paired payment duration"],
        ),
    )

    assert incomplete.level == ConfidenceLevel.LOW
    assert incomplete.score < complete.score
    assert incomplete.supporting_request_count == 0


def test_contradictions_materially_reduce_score():
    clean_logs = latency_logs()
    contradicted_logs = [*clean_logs]
    for index in range(6):
        contradicted_logs.append(
            log(f"payment:fast:{index}", f"latency-{index}", "payment-service", 120, 200)
        )

    clean = score(
        FailureType.PAYMENT_LATENCY,
        clean_logs,
        health=payment_health(),
        documents=[document(FailureType.PAYMENT_LATENCY)],
    )
    contradicted = score(
        FailureType.PAYMENT_LATENCY,
        contradicted_logs,
        health=payment_health(),
        documents=[document(FailureType.PAYMENT_LATENCY)],
    )

    assert contradicted.contradiction_penalty == 20
    assert clean.score - contradicted.score >= 20


def test_unverified_hypothesis_can_never_be_high():
    result = score(
        FailureType.PAYMENT_LATENCY,
        latency_logs(),
        verified=verification(False),
        health=payment_health(),
        documents=[document(FailureType.PAYMENT_LATENCY)],
    )

    assert result.score <= 54
    assert result.level == ConfidenceLevel.LOW


def test_deployment_metadata_alone_cannot_produce_high_confidence():
    deployment = Deployment(
        evidence_id="deployment:checkout:1.3.0",
        service="checkout-service",
        version="1.3.0",
        deployed_at=NOW - timedelta(hours=1),
        commit_sha="abc1234",
        summary="Checkout request correlation and timeout handling",
    )
    result = score(
        FailureType.BAD_DEPLOYMENT,
        [],
        deployments=[deployment],
        documents=[document(FailureType.BAD_DEPLOYMENT)],
    )

    assert result.level != ConfidenceLevel.HIGH
    assert result.runtime_support == 0
    assert "deployment_change" not in result.supporting_source_types


def test_strong_connection_exhaustion_is_high():
    logs = []
    for index in range(6):
        request_id = f"connection-{index}"
        logs.extend(
            [
                log(
                    f"checkout:{index}",
                    request_id,
                    "checkout-service",
                    35,
                    503,
                    "UpstreamPaymentHTTP503",
                ),
                log(
                    f"payment:{index}",
                    request_id,
                    "payment-service",
                    20,
                    503,
                    "ConnectionPoolExhausted",
                ),
            ]
        )
    result = score(
        FailureType.CONNECTION_EXHAUSTION,
        logs,
        health=payment_health("degraded", "available_connections=0"),
        documents=[document(FailureType.CONNECTION_EXHAUSTION)],
    )

    assert result.level == ConfidenceLevel.HIGH
    assert result.supporting_request_count == 6


def test_healthy_correlated_baseline_is_high():
    logs = []
    for index in range(6):
        request_id = f"healthy-{index}"
        logs.extend(
            [
                log(f"checkout:{index}", request_id, "checkout-service", 90, 200),
                log(f"payment:{index}", request_id, "payment-service", 60, 200),
            ]
        )
    health = [
        *payment_health(),
        ServiceHealth(
            evidence_id="health:checkout",
            service="checkout-service",
            status="healthy",
            checked_at=NOW,
            latency_ms=2,
        ),
    ]
    result = score(FailureType.HEALTHY, logs, health=health)

    assert result.level == ConfidenceLevel.HIGH
    assert result.score >= 80


def test_duplicate_logs_do_not_inflate_confidence():
    logs = latency_logs()
    original = score(FailureType.PAYMENT_LATENCY, logs, health=payment_health())
    duplicated = score(
        FailureType.PAYMENT_LATENCY,
        [*logs, *logs, *logs],
        health=payment_health(),
    )

    assert duplicated.score == original.score
    assert duplicated.supporting_request_count == original.supporting_request_count
    assert duplicated.total_relevant_request_count == original.total_relevant_request_count


def test_score_is_stable_across_model_wording():
    logs = latency_logs()
    first = score(
        FailureType.PAYMENT_LATENCY,
        logs,
        selected_hypothesis=hypothesis(
            FailureType.PAYMENT_LATENCY, title="Slow provider exceeds checkout budget"
        ),
    )
    second = score(
        FailureType.PAYMENT_LATENCY,
        logs,
        selected_hypothesis=hypothesis(
            FailureType.PAYMENT_LATENCY, title="Payment responses complete after caller timeout"
        ),
    )

    assert first == second


def test_llm_structured_schemas_do_not_author_numeric_confidence():
    assert "confidence" not in Hypothesis.model_json_schema()["properties"]
    assert "confidence" not in VerificationResult.model_json_schema()["properties"]
    assert "confidence" not in RootCauseReportDraft.model_json_schema()["properties"]


def test_confidence_level_thresholds_are_exact():
    assert confidence_level(0) == ConfidenceLevel.LOW
    assert confidence_level(54) == ConfidenceLevel.LOW
    assert confidence_level(55) == ConfidenceLevel.MEDIUM
    assert confidence_level(79) == ConfidenceLevel.MEDIUM
    assert confidence_level(80) == ConfidenceLevel.HIGH
    assert confidence_level(100) == ConfidenceLevel.HIGH
