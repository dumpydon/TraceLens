from __future__ import annotations

import re
from collections import defaultdict
from datetime import timedelta

from app.domain.models import (
    ConfidenceLevel,
    Deployment,
    EvidenceConfidence,
    FailureType,
    Hypothesis,
    Incident,
    LogEntry,
    RetrievedDocument,
    ServiceHealth,
    VerificationResult,
)

LOW_MAX = 54
MEDIUM_MAX = 79
RUNTIME_MAX = 55.0
CORROBORATION_MAX = 25.0
VERIFICATION_POINTS = 20.0


def confidence_level(score: int) -> ConfidenceLevel:
    if score <= LOW_MAX:
        return ConfidenceLevel.LOW
    if score <= MEDIUM_MAX:
        return ConfidenceLevel.MEDIUM
    return ConfidenceLevel.HIGH


def _group_requests(logs: list[LogEntry]) -> dict[str, list[LogEntry]]:
    grouped: dict[str, list[LogEntry]] = defaultdict(list)
    for log in logs:
        if log.request_id:
            grouped[log.request_id].append(log)
    return dict(grouped)


def _contains_error(logs: list[LogEntry], *errors: str) -> bool:
    return any(log.error_type in errors for log in logs)


def _request_supports(category: FailureType, logs: list[LogEntry]) -> bool:
    checkout = [log for log in logs if log.service == "checkout-service"]
    payment = [log for log in logs if log.service == "payment-service"]

    if category == FailureType.PAYMENT_LATENCY:
        checkout_timeouts = [
            log
            for log in checkout
            if log.error_type == "UpstreamPaymentTimeout"
            and log.status_code == 504
            and log.duration_ms >= 900
        ]
        late_successes = [
            log for log in payment if 200 <= log.status_code < 300 and log.duration_ms >= 900
        ]
        return any(
            payment_log.duration_ms >= checkout_log.duration_ms + 250
            for checkout_log in checkout_timeouts
            for payment_log in late_successes
        )

    if category == FailureType.CONNECTION_EXHAUSTION:
        return _contains_error(payment, "ConnectionPoolExhausted") and _contains_error(
            checkout, "UpstreamPaymentHTTP503"
        )

    if category == FailureType.PAYMENT_FAILURE:
        return _contains_error(payment, "ProviderDeclinedError") and _contains_error(
            checkout, "UpstreamPaymentHTTP502"
        )

    if category == FailureType.BAD_DEPLOYMENT:
        return _contains_error(payment, "ProviderConfigurationError") and _contains_error(
            checkout, "UpstreamPaymentHTTP500"
        )

    if category == FailureType.HEALTHY:
        services = {log.service for log in logs}
        return (
            {"checkout-service", "payment-service"}.issubset(services)
            and all(log.status_code < 500 and not log.error_type for log in logs)
            and all(log.duration_ms < 900 for log in logs)
        )

    return False


def _detail_number(details: str | None, key: str) -> float | None:
    if not details:
        return None
    match = re.search(rf"\b{re.escape(key)}\s*=\s*(-?\d+(?:\.\d+)?)", details)
    return float(match.group(1)) if match else None


def _health_supports(category: FailureType, health: list[ServiceHealth]) -> bool:
    payment = [item for item in health if item.service == "payment-service"]
    if category == FailureType.PAYMENT_LATENCY:
        return any(item.status == "healthy" for item in payment)
    if category == FailureType.CONNECTION_EXHAUSTION:
        for item in payment:
            available_connections = _detail_number(item.details, "available_connections")
            if item.status != "healthy" or (
                available_connections is not None and available_connections <= 1
            ):
                return True
        return False
    if category == FailureType.BAD_DEPLOYMENT:
        return any(
            item.status != "healthy"
            or "provider_configured=False" in (item.details or "")
            for item in payment
        )
    if category == FailureType.HEALTHY:
        return bool(health) and all(item.status == "healthy" for item in health)
    return False


def _deployment_supports(
    category: FailureType,
    deployments: list[Deployment],
    incident: Incident | None,
    has_runtime_support: bool,
) -> bool:
    if category != FailureType.BAD_DEPLOYMENT or not incident or not has_runtime_support:
        return False
    relevant_terms = ("config", "credential", "provider", "endpoint")
    return any(
        deployment.service == "payment-service"
        and abs(incident.started_at - deployment.deployed_at) <= timedelta(hours=24)
        and any(term in deployment.summary.lower() for term in relevant_terms)
        for deployment in deployments
    )


def _supporting_sources(
    category: FailureType,
    grouped: dict[str, list[LogEntry]],
    supporting_ids: set[str],
    health: list[ServiceHealth],
    deployments: list[Deployment],
    documents: list[RetrievedDocument],
    incident: Incident | None,
) -> list[str]:
    sources: set[str] = set()
    supporting_logs = [log for request_id in supporting_ids for log in grouped[request_id]]
    if supporting_logs:
        sources.add("runtime_logs")
    if _health_supports(category, health):
        sources.add("health_checks")
    if _deployment_supports(category, deployments, incident, bool(supporting_ids)):
        sources.add("deployment_change")
    for document in documents:
        if document.failure_type == category.value:
            sources.add(f"operational_{document.document_type}")
    return sorted(sources)


def _contradictions(
    category: FailureType,
    grouped: dict[str, list[LogEntry]],
    supporting_ids: set[str],
    health: list[ServiceHealth],
    verification: VerificationResult,
) -> set[str]:
    contradictions = {f"citation:{item}" for item in verification.contradicted_evidence_ids}

    if category == FailureType.PAYMENT_LATENCY:
        for request_id, logs in grouped.items():
            checkout_timeout = any(
                log.service == "checkout-service"
                and log.error_type == "UpstreamPaymentTimeout"
                for log in logs
            )
            fast_payment = any(
                log.service == "payment-service"
                and log.status_code == 200
                and log.duration_ms < 900
                for log in logs
            )
            if checkout_timeout and fast_payment:
                contradictions.add(f"fast_payment:{request_id}")
        payment_logs = [
            log for logs in grouped.values() for log in logs if log.service == "payment-service"
        ]
        if (
            not supporting_ids
            and payment_logs
            and all(log.duration_ms < 900 for log in payment_logs)
        ):
            contradictions.add("consistently_fast_payments")

    elif category == FailureType.CONNECTION_EXHAUSTION and not supporting_ids:
        if any(
            item.service == "payment-service"
            and item.status == "healthy"
            and (_detail_number(item.details, "available_connections") or 0) >= 10
            for item in health
        ):
            contradictions.add("normal_connection_capacity")

    elif category == FailureType.PAYMENT_FAILURE and not supporting_ids:
        payment_logs = [
            log for logs in grouped.values() for log in logs if log.service == "payment-service"
        ]
        if payment_logs and all(log.status_code < 300 and not log.error_type for log in payment_logs):
            contradictions.add("successful_payments")

    elif category == FailureType.BAD_DEPLOYMENT and not supporting_ids:
        contradictions.add("no_runtime_configuration_failure")

    elif category == FailureType.HEALTHY:
        for request_id, logs in grouped.items():
            if any(log.status_code >= 500 or log.error_type or log.duration_ms >= 900 for log in logs):
                contradictions.add(f"abnormal_request:{request_id}")

    return contradictions


def calculate_evidence_confidence(
    *,
    hypothesis: Hypothesis,
    verification: VerificationResult,
    logs: list[LogEntry],
    service_health: list[ServiceHealth],
    deployments: list[Deployment],
    retrieved_documents: list[RetrievedDocument],
    incident: Incident | None = None,
) -> EvidenceConfidence:
    """Calculate a transparent support score from collected evidence.

    The score is deterministic and intentionally not a calibrated probability. Runtime support
    is computed over unique request IDs, with quantity credit saturating at six supporting
    requests so duplicate or unusually large batches cannot inflate the result without bound.
    """

    try:
        category = FailureType(hypothesis.suspected_failure_type)
    except ValueError:
        unresolved_count = max(1, len(verification.unresolved_questions))
        return EvidenceConfidence(
            score=0,
            level=ConfidenceLevel.LOW,
            runtime_support=0,
            corroboration=0,
            verification_support=0,
            contradiction_penalty=0,
            uncertainty_penalty=min(15, 3 * unresolved_count),
            supporting_request_count=0,
            total_relevant_request_count=len(_group_requests(logs)),
            supporting_source_types=[],
            contradiction_count=0,
            unresolved_question_count=unresolved_count,
            explanation=(
                "The legacy failure type is not a supported V1 category, so category-specific "
                "evidence confidence cannot be calculated. This is not a calibrated probability."
            ),
        )
    grouped = _group_requests(logs)
    supporting_ids = {
        request_id
        for request_id, request_logs in grouped.items()
        if _request_supports(category, request_logs)
    }
    total_requests = len(grouped)
    support_ratio = len(supporting_ids) / total_requests if total_requests else 0.0
    quantity_saturation = min(len(supporting_ids) / 6, 1.0)
    runtime_support = round(
        RUNTIME_MAX * (0.55 * support_ratio + 0.45 * quantity_saturation), 2
    )

    source_types = _supporting_sources(
        category,
        grouped,
        supporting_ids,
        service_health,
        deployments,
        retrieved_documents,
        incident,
    )
    corroboration = round(
        CORROBORATION_MAX * min(len(source_types) / 3, 1.0), 2
    )
    verification_support = VERIFICATION_POINTS if verification.is_sufficient else 0.0

    contradictions = _contradictions(
        category, grouped, supporting_ids, service_health, verification
    )
    contradiction_penalty = float(min(20, 4 * len(contradictions)))
    unresolved = {item.strip() for item in verification.unresolved_questions if item.strip()}
    missing = {item.strip() for item in hypothesis.missing_evidence if item.strip()}
    uncertainty_penalty = float(min(15, 3 * len(unresolved) + 2 * len(missing)))

    score = round(
        runtime_support
        + corroboration
        + verification_support
        - contradiction_penalty
        - uncertainty_penalty
    )
    score = max(0, min(100, score))
    if not verification.is_sufficient:
        score = min(score, LOW_MAX)

    explanation = (
        f"{len(supporting_ids)}/{total_requests} unique correlated requests support "
        f"{category.value}; {len(source_types)} supporting source types; "
        f"{len(contradictions)} contradictions; {len(unresolved)} unresolved questions. "
        "This deterministic support score is not a calibrated probability."
    )
    return EvidenceConfidence(
        score=score,
        level=confidence_level(score),
        runtime_support=runtime_support,
        corroboration=corroboration,
        verification_support=verification_support,
        contradiction_penalty=contradiction_penalty,
        uncertainty_penalty=uncertainty_penalty,
        supporting_request_count=len(supporting_ids),
        total_relevant_request_count=total_requests,
        supporting_source_types=source_types,
        contradiction_count=len(contradictions),
        unresolved_question_count=len(unresolved),
        explanation=explanation,
    )
