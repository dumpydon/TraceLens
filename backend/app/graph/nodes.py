from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from typing import Any

from app.core.config import Settings, get_settings
from app.core.database import Database, get_database
from app.domain.models import (
    EvidenceItem,
    EvidenceKind,
    FailureType,
    Hypothesis,
    IncidentStatus,
    InvestigationEvent,
    InvestigationEventType,
    ReportEvidence,
    RootCauseReport,
    RootCauseReportDraft,
    RuntimeAnalysis,
    VerificationResult,
)
from app.graph.prompts import (
    HYPOTHESIS_PROMPT,
    REPORT_PROMPT,
    RUNTIME_ANALYSIS_PROMPT,
    VERIFICATION_PROMPT,
)
from app.graph.state import InvestigationState
from app.rag.retriever import retrieve_documents
from app.services.evidence_confidence import calculate_evidence_confidence
from app.services.model_reasoning import StructuredReasoner
from app.services.runtime_context import collect_health, read_deployments, read_logs


def _model_payload(items: list[Any]) -> list[dict]:
    return [item.model_dump(mode="json") for item in items]


def _reasoning_payload(item: Any) -> dict:
    """Exclude historical model confidence fields from downstream LLM context."""
    return item.model_dump(mode="json", exclude={"confidence", "evidence_confidence"})


class InvestigationNodes:
    def __init__(self, database: Database | None = None, settings: Settings | None = None):
        self.settings = settings or get_settings()
        self.database = database or get_database()
        self.reasoner = StructuredReasoner(self.settings)

    async def emit(
        self,
        state: InvestigationState,
        event_type: InvestigationEventType,
        stage: str,
        summary: str,
        metadata: dict | None = None,
    ) -> None:
        await self.database.aadd_event(
            InvestigationEvent(
                event_type=event_type,
                incident_id=state["incident_id"],
                stage=stage,
                summary=summary,
                metadata=metadata or {},
            )
        )

    async def load_incident(self, state: InvestigationState) -> dict:
        incident = await self.database.aget_incident(state["incident_id"])
        if not incident:
            raise ValueError(f"Incident {state['incident_id']} does not exist")
        await self.database.aupdate_incident_status(incident.id, IncidentStatus.INVESTIGATING)
        incident.status = IncidentStatus.INVESTIGATING
        await self.emit(
            state,
            InvestigationEventType.CONTEXT_COLLECTION_STARTED,
            "context",
            "Loading incident and runtime sources",
        )
        return {"incident": incident}

    async def collect_runtime_context(self, state: InvestigationState) -> dict:
        incident = state["incident"]
        errors = list(state["errors"])
        if incident and (incident.traffic_batch_id or incident.observation_started_at):
            logs = await asyncio.to_thread(
                read_logs,
                self.settings.runtime_directory,
                traffic_batch_id=incident.traffic_batch_id,
                observation_started_at=incident.observation_started_at,
                observation_ended_at=incident.observation_ended_at,
            )
        else:
            logs = []
            errors.append(
                "incident_evidence_scope_missing: legacy incident has no traffic batch or observation window"
            )
        deployments = await asyncio.to_thread(
            read_deployments,
            self.settings.runtime_directory,
            as_of=incident.observation_ended_at if incident else None,
        )
        health = await collect_health(self.settings)
        evidence = [
            EvidenceItem(
                id=log.evidence_id,
                kind=EvidenceKind.LOG,
                source=log.service,
                summary=(
                    f"{log.event}: status {log.status_code}, {log.duration_ms:.0f} ms"
                    + (f", {log.error_type}" if log.error_type else "")
                ),
                timestamp=log.timestamp,
                details={
                    "request_id": log.request_id,
                    "traffic_batch_id": log.traffic_batch_id,
                    "duration_ms": log.duration_ms,
                    "status_code": log.status_code,
                    "error_type": log.error_type,
                    "deployment_version": log.deployment_version,
                },
            )
            for log in logs
        ]
        evidence.extend(
            EvidenceItem(
                id=deployment.evidence_id,
                kind=EvidenceKind.DEPLOYMENT,
                source=deployment.service,
                summary=f"Version {deployment.version}: {deployment.summary}",
                timestamp=deployment.deployed_at,
                details=deployment.model_dump(mode="json"),
            )
            for deployment in deployments
        )
        evidence.extend(
            EvidenceItem(
                id=item.evidence_id,
                kind=EvidenceKind.HEALTH,
                source=item.service,
                summary=f"Health {item.status} in {item.latency_ms:.0f} ms"
                + (f" ({item.details})" if item.details else ""),
                timestamp=item.checked_at,
                details=item.model_dump(mode="json"),
            )
            for item in health
        )
        await self.emit(
            state,
            InvestigationEventType.LOGS_COLLECTED,
            "context",
            f"Collected {len(logs)} correlated request logs",
            {"count": len(logs)},
        )
        await self.emit(
            state,
            InvestigationEventType.DEPLOYMENT_FOUND,
            "context",
            f"Loaded {len(deployments)} deployment records and {len(health)} health checks",
            {"deployments": len(deployments), "health_checks": len(health)},
        )
        return {
            "logs": logs,
            "deployments": deployments,
            "service_health": health,
            "evidence": evidence,
            "errors": errors,
        }

    async def analyze_runtime_evidence(self, state: InvestigationState) -> dict:
        fallback = self._fallback_analysis(state)
        errors = list(state["errors"])
        analysis = fallback
        if self.reasoner.enabled:
            try:
                analysis = await self.reasoner.invoke(
                    RuntimeAnalysis,
                    RUNTIME_ANALYSIS_PROMPT,
                    {
                        "incident": self._safe_incident(state),
                        "logs": _model_payload(state["logs"]),
                        "deployments": _model_payload(state["deployments"]),
                        "service_health": _model_payload(state["service_health"]),
                    },
                )
                analysis, citation_errors = self._validate_analysis(analysis, state["evidence"])
                errors.extend(citation_errors)
            except Exception as exc:  # noqa: BLE001 - model boundary must record provider failures
                errors.append(f"runtime_analysis_structured_output: {type(exc).__name__}: {exc}")
                analysis = fallback
        await self.emit(
            state,
            InvestigationEventType.RUNTIME_ANALYSIS_COMPLETED,
            "runtime",
            analysis.anomaly_summary,
            {"signals": analysis.failure_signals},
        )
        return {
            "runtime_analysis": analysis,
            "retrieval_query": analysis.retrieval_query,
            "errors": errors,
        }

    async def retrieve_operational_knowledge(self, state: InvestigationState) -> dict:
        await self.emit(
            state,
            InvestigationEventType.RETRIEVAL_STARTED,
            "retrieval",
            "Searching operational knowledge with MMR",
        )
        errors = list(state["errors"])
        try:
            documents = await retrieve_documents(state["retrieval_query"], settings=self.settings)
        except Exception as exc:  # noqa: BLE001 - retrieval boundary records integration failures
            documents = []
            errors.append(f"retrieval: {type(exc).__name__}: {exc}")
        non_document_evidence = [
            item for item in state["evidence"] if item.kind != EvidenceKind.DOCUMENT
        ]
        document_evidence = [
            EvidenceItem(
                id=document.evidence_id,
                kind=EvidenceKind.DOCUMENT,
                source=document.source,
                summary=document.content[:240],
                details={
                    "document_type": document.document_type,
                    "service": document.service,
                    "failure_type": document.failure_type,
                },
            )
            for document in documents
        ]
        await self.emit(
            state,
            InvestigationEventType.DOCUMENTS_RETRIEVED,
            "retrieval",
            f"Retrieved {len(documents)} relevant operational passages",
            {"evidence_ids": [doc.evidence_id for doc in documents]},
        )
        return {
            "retrieved_documents": documents,
            "evidence": non_document_evidence + document_evidence,
            "errors": errors,
        }

    async def generate_hypothesis(self, state: InvestigationState) -> dict:
        fallback = self._fallback_hypothesis(state)
        errors = list(state["errors"])
        hypothesis = fallback
        if self.reasoner.enabled:
            try:
                hypothesis = await self.reasoner.invoke(
                    Hypothesis,
                    HYPOTHESIS_PROMPT,
                    {
                        "runtime_analysis": state["runtime_analysis"].model_dump(mode="json"),
                        "evidence": _model_payload(state["evidence"]),
                    },
                )
                valid_ids, invalid_ids = self._resolve_ids(
                    hypothesis.supporting_evidence_ids, state["evidence"]
                )
                if invalid_ids:
                    errors.append(f"hypothesis_unknown_evidence_ids: {','.join(invalid_ids)}")
                hypothesis.supporting_evidence_ids = valid_ids
                if not valid_ids:
                    hypothesis = fallback
            except Exception as exc:  # noqa: BLE001 - model boundary must record provider failures
                errors.append(f"hypothesis_structured_output: {type(exc).__name__}: {exc}")
                hypothesis = fallback
        await self.emit(
            state,
            InvestigationEventType.HYPOTHESIS_GENERATED,
            "hypothesis",
            hypothesis.title,
            {
                "suspected_service": hypothesis.suspected_service,
                "failure_type": hypothesis.suspected_failure_type,
                "iteration": state["iteration_count"] + 1,
            },
        )
        return {
            "active_hypothesis": hypothesis,
            "hypotheses": [*state["hypotheses"], hypothesis],
            "iteration_count": state["iteration_count"] + 1,
            "errors": errors,
        }

    async def verify_hypothesis(self, state: InvestigationState) -> dict:
        await self.emit(
            state,
            InvestigationEventType.VERIFICATION_STARTED,
            "verify",
            "Checking hypothesis citations against collected evidence",
        )
        fallback = self._fallback_verification(state)
        errors = list(state["errors"])
        verification = fallback
        if self.reasoner.enabled:
            try:
                verification = await self.reasoner.invoke(
                    VerificationResult,
                    VERIFICATION_PROMPT,
                    {
                        "hypothesis": _reasoning_payload(state["active_hypothesis"]),
                        "evidence": _model_payload(state["evidence"]),
                    },
                )
                valid_ids, invalid_ids = self._resolve_ids(
                    verification.supported_evidence_ids, state["evidence"]
                )
                if invalid_ids:
                    errors.append(f"verification_unknown_evidence_ids: {','.join(invalid_ids)}")
                supporting_ids = self._supporting_runtime_ids(
                    state["active_hypothesis"].suspected_failure_type,
                    state["evidence"],
                    valid_ids,
                )
                verification.supported_evidence_ids = supporting_ids
                category_support_is_sufficient = self._has_sufficient_support(
                    state["active_hypothesis"].suspected_failure_type,
                    supporting_ids,
                    state["evidence"],
                )
                verification.is_sufficient = (
                    verification.is_sufficient and category_support_is_sufficient
                )
                if not verification.is_sufficient:
                    verification.evidence_support = (
                        "Evidence is insufficient to verify the hypothesis: "
                        f"only {len(supporting_ids)} category-specific runtime records were found; "
                        "the required correlated support is absent."
                    )
                    if not verification.unresolved_questions:
                        verification.unresolved_questions = [
                            "Which additional runtime evidence directly supports this category?"
                        ]
            except Exception as exc:  # noqa: BLE001 - model boundary must record provider failures
                errors.append(f"verification_structured_output: {type(exc).__name__}: {exc}")
                verification = fallback
        await self.emit(
            state,
            InvestigationEventType.VERIFICATION_COMPLETED,
            "verify",
            "Evidence is sufficient" if verification.is_sufficient else "Evidence needs refinement",
            {
                "sufficient": verification.is_sufficient,
                "iteration": state["iteration_count"],
            },
        )
        evidence_confidence = calculate_evidence_confidence(
            hypothesis=state["active_hypothesis"],
            verification=verification,
            logs=state["logs"],
            service_health=state["service_health"],
            deployments=state["deployments"],
            retrieved_documents=state["retrieved_documents"],
            incident=state["incident"],
        )
        return {
            "verification": verification,
            "evidence_confidence": evidence_confidence,
            "errors": errors,
        }

    async def refine_investigation(self, state: InvestigationState) -> dict:
        questions = state["verification"].unresolved_questions if state["verification"] else []
        query = " ".join(
            [
                state["retrieval_query"],
                state["active_hypothesis"].suspected_failure_type,
                *questions,
            ]
        ).strip()
        await self.emit(
            state,
            InvestigationEventType.INVESTIGATION_REFINED,
            "refine",
            f"Refining evidence search for attempt {state['iteration_count'] + 1}",
            {"unresolved_questions": questions},
        )
        return {"retrieval_query": query}

    async def generate_report(self, state: InvestigationState) -> dict:
        fallback = self._fallback_report(state)
        errors = list(state["errors"])
        report = fallback
        evidence_confidence = state.get("evidence_confidence") or calculate_evidence_confidence(
            hypothesis=state["active_hypothesis"],
            verification=state["verification"],
            logs=state["logs"],
            service_health=state["service_health"],
            deployments=state["deployments"],
            retrieved_documents=state["retrieved_documents"],
            incident=state["incident"],
        )
        category = self._canonical_failure_type(state["active_hypothesis"].suspected_failure_type)
        if self.reasoner.enabled and state["verification"].is_sufficient and category is not None:
            try:
                draft = await self.reasoner.invoke(
                    RootCauseReportDraft,
                    REPORT_PROMPT,
                    {
                        "incident_id": state["incident_id"],
                        "hypothesis": _reasoning_payload(state["active_hypothesis"]),
                        "verification": _reasoning_payload(state["verification"]),
                        "evidence": _model_payload(state["evidence"]),
                        "required_incident_id": state["incident_id"],
                    },
                )
                report = RootCauseReport(
                    incident_id=state["incident_id"],
                    evidence_confidence=evidence_confidence,
                    **draft.model_dump(),
                )
                report.root_cause_category = category.value
                valid = {item.id for item in state["evidence"]}
                report.evidence = [item for item in report.evidence if item.evidence_id in valid]
                if not report.evidence:
                    errors.append(
                        "report_unknown_evidence_ids: all model citations were unresolved"
                    )
                    report = fallback
            except Exception as exc:  # noqa: BLE001 - model boundary must record provider failures
                errors.append(f"report_structured_output: {type(exc).__name__}: {exc}")
                report = fallback
        if (
            state["iteration_count"] >= state["max_iterations"]
            and not state["verification"].is_sufficient
        ):
            report.limitations.append(
                "Maximum investigation attempts reached before full verification."
            )
        if not self.reasoner.enabled:
            report.limitations.append(
                "Generated by the deterministic local reasoner because OPENAI_API_KEY is not configured."
            )
        await self.database.asave_report(report)
        await self.database.aupdate_incident_status(state["incident_id"], IncidentStatus.RESOLVED)
        await self.emit(
            state,
            InvestigationEventType.REPORT_GENERATED,
            "report",
            f"Root-cause report generated with {len(report.evidence)} evidence citations",
            {
                "evidence_confidence_score": evidence_confidence.score,
                "evidence_confidence_level": evidence_confidence.level,
            },
        )
        await self.emit(
            state,
            InvestigationEventType.INVESTIGATION_COMPLETED,
            "report",
            "Investigation completed",
        )
        return {
            "final_report": report,
            "evidence_confidence": evidence_confidence,
            "errors": errors,
        }

    @staticmethod
    def _safe_incident(state: InvestigationState) -> dict:
        incident = state["incident"]
        if not incident:
            return {}
        return {
            "id": incident.id,
            "title": incident.title,
            "service": incident.service,
            "severity": incident.severity,
            "started_at": incident.started_at,
            "summary": incident.summary,
        }

    @staticmethod
    def _resolve_ids(ids: list[str], evidence: list[EvidenceItem]) -> tuple[list[str], list[str]]:
        available = {item.id for item in evidence}
        return [item for item in ids if item in available], [
            item for item in ids if item not in available
        ]

    @staticmethod
    def _canonical_failure_type(value: FailureType | str) -> FailureType | None:
        try:
            return FailureType(value)
        except ValueError:
            return None

    def _validate_analysis(
        self, analysis: RuntimeAnalysis, evidence: list[EvidenceItem]
    ) -> tuple[RuntimeAnalysis, list[str]]:
        valid, invalid = self._resolve_ids(analysis.relevant_evidence_ids, evidence)
        analysis.relevant_evidence_ids = valid
        errors = [f"runtime_analysis_unknown_evidence_ids: {','.join(invalid)}"] if invalid else []
        return analysis, errors

    @staticmethod
    def _pattern_request_ids(logs: list) -> dict[FailureType, set[str]]:
        patterns: dict[FailureType, set[str]] = {
            FailureType.BAD_DEPLOYMENT: set(),
            FailureType.CONNECTION_EXHAUSTION: set(),
            FailureType.PAYMENT_FAILURE: set(),
            FailureType.PAYMENT_LATENCY: set(),
        }
        for log in logs:
            if log.error_type in {"ProviderConfigurationError", "UpstreamPaymentHTTP500"}:
                patterns[FailureType.BAD_DEPLOYMENT].add(log.request_id)
            if log.error_type in {"ConnectionPoolExhausted", "UpstreamPaymentHTTP503"}:
                patterns[FailureType.CONNECTION_EXHAUSTION].add(log.request_id)
            if log.error_type in {"ProviderDeclinedError", "UpstreamPaymentHTTP502"}:
                patterns[FailureType.PAYMENT_FAILURE].add(log.request_id)
            if log.error_type == "UpstreamPaymentTimeout" or (
                log.service == "payment-service" and log.duration_ms >= 900
            ):
                patterns[FailureType.PAYMENT_LATENCY].add(log.request_id)
        return patterns

    @classmethod
    def _dominant_failure_type(cls, logs: list) -> FailureType:
        patterns = cls._pattern_request_ids(logs)
        category, request_ids = max(patterns.items(), key=lambda item: len(item[1]))
        return category if request_ids else FailureType.HEALTHY

    @staticmethod
    def _log_supports_category(log, category: FailureType | str) -> bool:
        category = InvestigationNodes._canonical_failure_type(category)
        if category == FailureType.BAD_DEPLOYMENT:
            return log.error_type in {"ProviderConfigurationError", "UpstreamPaymentHTTP500"}
        if category == FailureType.CONNECTION_EXHAUSTION:
            return log.error_type in {"ConnectionPoolExhausted", "UpstreamPaymentHTTP503"}
        if category == FailureType.PAYMENT_FAILURE:
            return log.error_type in {"ProviderDeclinedError", "UpstreamPaymentHTTP502"}
        if category == FailureType.PAYMENT_LATENCY:
            return log.error_type == "UpstreamPaymentTimeout" or (
                log.service == "payment-service" and log.duration_ms >= 900
            )
        if category == FailureType.HEALTHY:
            return log.status_code < 500 and log.duration_ms < 900
        return False

    @staticmethod
    def _evidence_supports_category(item: EvidenceItem, category: FailureType | str) -> bool:
        category = InvestigationNodes._canonical_failure_type(category)
        if item.kind == EvidenceKind.LOG:
            error_type = item.details.get("error_type")
            service = item.source
            duration_ms = float(item.details.get("duration_ms", 0))
            status_code = int(item.details.get("status_code", 0))
            if category == FailureType.BAD_DEPLOYMENT:
                return error_type in {"ProviderConfigurationError", "UpstreamPaymentHTTP500"}
            if category == FailureType.CONNECTION_EXHAUSTION:
                return error_type in {"ConnectionPoolExhausted", "UpstreamPaymentHTTP503"}
            if category == FailureType.PAYMENT_FAILURE:
                return error_type in {"ProviderDeclinedError", "UpstreamPaymentHTTP502"}
            if category == FailureType.PAYMENT_LATENCY:
                return error_type == "UpstreamPaymentTimeout" or (
                    service == "payment-service" and duration_ms >= 900
                )
            if category == FailureType.HEALTHY:
                return status_code < 500 and duration_ms < 900
            return False
        if category == FailureType.HEALTHY and item.kind == EvidenceKind.HEALTH:
            return item.details.get("status") == "healthy"
        return False

    @classmethod
    def _supporting_runtime_ids(
        cls,
        category: FailureType | str,
        evidence: list[EvidenceItem],
        candidate_ids: list[str] | None = None,
    ) -> list[str]:
        candidates = set(candidate_ids) if candidate_ids is not None else None
        return [
            item.id
            for item in evidence
            if (candidates is None or item.id in candidates)
            and cls._evidence_supports_category(item, category)
        ]

    @classmethod
    def _has_sufficient_support(
        cls, category: FailureType | str, supporting_ids: list[str], evidence: list[EvidenceItem]
    ) -> bool:
        category = cls._canonical_failure_type(category)
        if category is None:
            return False
        if category == FailureType.HEALTHY:
            return len(supporting_ids) >= 1
        evidence_map = {item.id: item for item in evidence}
        request_ids = {
            evidence_map[item_id].details.get("request_id")
            for item_id in supporting_ids
            if item_id in evidence_map and evidence_map[item_id].details.get("request_id")
        }
        return len(request_ids) >= 2

    @staticmethod
    def _fallback_analysis(state: InvestigationState) -> RuntimeAnalysis:
        error_logs = [log for log in state["logs"] if log.status_code >= 500 or log.error_type]
        slow_logs = [log for log in state["logs"] if log.duration_ms >= 900]
        degraded = [item for item in state["service_health"] if item.status != "healthy"]
        signals = sorted(
            {log.error_type for log in error_logs if log.error_type}
            | (
                {"high payment latency"}
                if any(log.service == "payment-service" for log in slow_logs)
                else set()
            )
            | {f"{item.service} health {item.status}" for item in degraded}
        )
        if any(log.error_type == "ProviderConfigurationError" for log in error_logs):
            payment_deployment = next(
                (
                    deployment
                    for deployment in state["deployments"]
                    if deployment.service == "payment-service"
                ),
                None,
            )
            if payment_deployment:
                signals.append(
                    f"payment deployment {payment_deployment.version} {payment_deployment.summary}"
                )
        dominant_category = InvestigationNodes._dominant_failure_type(state["logs"])
        dominant_logs = [
            log
            for log in state["logs"]
            if InvestigationNodes._log_supports_category(log, dominant_category)
        ]
        ids = [item.evidence_id for item in [*dominant_logs[-18:], *degraded]]
        ids = list(dict.fromkeys(ids))
        services = sorted({item.service for item in [*error_logs, *slow_logs, *degraded]})
        if signals:
            summary = (
                f"Observed {len(error_logs)} failed and {len(slow_logs)} slow requests: "
                + "; ".join(signals)
            )
        else:
            summary = "No material runtime anomaly is present in the collected window."
            ids = [item.evidence_id for item in state["service_health"]]
            services = [item.service for item in state["service_health"]]
        query = (
            " ".join([*services, dominant_category, *signals])
            or "healthy checkout payment baseline"
        )
        return RuntimeAnalysis(
            anomaly_summary=summary,
            affected_services=services,
            failure_signals=signals,
            relevant_evidence_ids=ids,
            retrieval_query=query,
        )

    @classmethod
    def _fallback_hypothesis(cls, state: InvestigationState) -> Hypothesis:
        logs = state["logs"]
        health = state["service_health"]
        category = cls._dominant_failure_type(logs)
        title = {
            FailureType.BAD_DEPLOYMENT: "Payment provider configuration regression",
            FailureType.CONNECTION_EXHAUSTION: "Payment provider connections exhausted",
            FailureType.PAYMENT_FAILURE: "Payment provider is rejecting charges",
            FailureType.PAYMENT_LATENCY: "Payment latency exceeds checkout timeout budget",
            FailureType.HEALTHY: "No supported service fault in the evidence window",
        }[category]
        runtime_ids = [
            log.evidence_id for log in logs if cls._log_supports_category(log, category)
        ][-18:]
        if category == FailureType.HEALTHY and not runtime_ids:
            runtime_ids = [item.evidence_id for item in health if item.status == "healthy"]
        ordered_documents = sorted(
            state["retrieved_documents"],
            key=lambda document: document.failure_type != category,
        )
        document_ids = [doc.evidence_id for doc in ordered_documents[:2]]
        ids = list(dict.fromkeys([*runtime_ids, *document_ids]))
        if not ids:
            ids = [item.evidence_id for item in health[:2]]
        return Hypothesis(
            title=title,
            suspected_service="payment-service" if category != FailureType.HEALTHY else "none",
            suspected_failure_type=category,
            reasoning_summary=(
                "Correlated payment and checkout evidence matches the operational failure pattern."
                if category != FailureType.HEALTHY
                else "Collected health and request evidence does not support an active failure."
            ),
            supporting_evidence_ids=ids,
            missing_evidence=[]
            if len(runtime_ids) >= 2
            else ["Additional correlated failing requests"],
        )

    @classmethod
    def _fallback_verification(cls, state: InvestigationState) -> VerificationResult:
        hypothesis = state["active_hypothesis"]
        evidence_map = {item.id: item for item in state["evidence"]}
        resolved = [item for item in hypothesis.supporting_evidence_ids if item in evidence_map]
        supported = cls._supporting_runtime_ids(
            hypothesis.suspected_failure_type,
            state["evidence"],
            resolved,
        )
        sufficient = cls._has_sufficient_support(
            hypothesis.suspected_failure_type,
            supported,
            state["evidence"],
        )
        evidence_support = (
            f"Resolved {len(resolved)} citations; {len(supported)} category-specific runtime "
            f"records support {hypothesis.suspected_failure_type}."
            if sufficient
            else (
                "Evidence is insufficient to verify the hypothesis: "
                f"only {len(supported)} category-specific runtime records were found; "
                "the required correlated support is absent."
            )
        )
        return VerificationResult(
            is_sufficient=sufficient,
            evidence_support=evidence_support,
            supported_evidence_ids=supported,
            unresolved_questions=[]
            if sufficient
            else ["Which additional runtime signal confirms this pattern?"],
        )

    @classmethod
    def _fallback_report(cls, state: InvestigationState) -> RootCauseReport:
        hypothesis = state["active_hypothesis"]
        verification = state["verification"]
        raw_category = hypothesis.suspected_failure_type
        canonical_category = cls._canonical_failure_type(raw_category)
        category = canonical_category.value if canonical_category else str(raw_category)
        evidence_map = {item.id: item for item in state["evidence"]}
        evidence = [
            ReportEvidence(evidence_id=item_id, claim=evidence_map[item_id].summary)
            for item_id in hypothesis.supporting_evidence_ids
            if item_id in evidence_map
        ]
        if not evidence:
            first = state["evidence"][0]
            evidence = [ReportEvidence(evidence_id=first.id, claim=first.summary)]
        actions: dict[str, list[str]] = {
            "payment_latency": [
                "Inspect provider latency and route away from the degraded dependency.",
                "Review idempotency for authorizations completing after checkout timeout.",
            ],
            "payment_failure": [
                "Confirm provider availability and error response rates.",
                "Apply the documented payment provider failover procedure if failures persist.",
            ],
            "bad_deployment": [
                "Validate the payment provider endpoint and credential mapping.",
                "Use the normal human-controlled process to restore the last known-good release.",
            ],
            "connection_exhaustion": [
                "Inspect provider pool limits and connection release behavior.",
                "Reduce concurrency while restoring provider connection capacity.",
            ],
            "healthy": ["Continue monitoring; no remediation is supported by current evidence."],
        }
        limitations = list(hypothesis.missing_evidence)
        verified = bool(verification.is_sufficient and canonical_category is not None)
        if canonical_category is None:
            limitations.append(
                f"Legacy failure type '{category}' is not a supported V1 category and was not remapped."
            )
        if not verified:
            limitations.append("The available evidence was insufficient to verify this hypothesis.")
        evidence_confidence = state.get("evidence_confidence") or calculate_evidence_confidence(
            hypothesis=hypothesis,
            verification=verification,
            logs=state["logs"],
            service_health=state["service_health"],
            deployments=state["deployments"],
            retrieved_documents=state["retrieved_documents"],
            incident=state["incident"],
        )
        return RootCauseReport(
            incident_id=state["incident_id"],
            root_cause=hypothesis.title
            if verified
            else f"Unverified hypothesis: {hypothesis.title}",
            root_cause_category=category,
            affected_service=hypothesis.suspected_service,
            summary=(
                hypothesis.reasoning_summary
                if verified
                else "The investigation reached its evidence limit without establishing a supported root cause."
            ),
            evidence_confidence=evidence_confidence,
            evidence=evidence,
            recommended_actions=(
                actions[category]
                if verified
                else [
                    "Preserve the collected evidence and obtain category-specific runtime confirmation.",
                    "Do not attribute the incident to a deployment or service without direct evidence.",
                ]
            ),
            limitations=limitations,
            generated_at=datetime.now(UTC),
        )
