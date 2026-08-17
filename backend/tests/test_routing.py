from app.domain.models import (
    EvidenceItem,
    EvidenceKind,
    FailureType,
    Hypothesis,
    Incident,
    IncidentStatus,
    VerificationResult,
)
from app.graph.nodes import InvestigationNodes
from app.graph.routing import route_after_verification
from app.graph.state import initial_state


def test_routes_to_report_when_evidence_is_sufficient():
    state = initial_state("INC-1")
    state["verification"] = VerificationResult(
        is_sufficient=True,
        evidence_support="supported",
        supported_evidence_ids=["log:1"],
    )
    assert route_after_verification(state) == "generate_report"


def test_maximum_iteration_forces_bounded_report():
    state = initial_state("INC-1", max_iterations=3)
    state["iteration_count"] = 3
    state["verification"] = VerificationResult(
        is_sufficient=False,
        evidence_support="weak",
        supported_evidence_ids=[],
        unresolved_questions=["more evidence"],
    )
    assert route_after_verification(state) == "generate_report"


def test_reasoning_payload_excludes_incident_presentation_and_control_metadata():
    state = initial_state("INC-PRESENTED")
    state["incident"] = Incident(
        id="INC-PRESENTED",
        title="Checkout timeouts with delayed payment responses",
        summary="Repeated checkout 504s observed with delayed payment responses.",
        service="checkout-service",
        severity="high",
        scenario_label="payment_latency",
    )

    payload = InvestigationNodes._safe_incident(state)

    assert payload["id"] == "INC-PRESENTED"
    assert payload["service"] == "checkout-service"
    assert "title" not in payload
    assert "summary" not in payload
    assert "scenario_label" not in payload


async def test_maximum_iteration_generates_safe_terminal_report(settings, database):
    incident = Incident(
        id="INC-MAX-ITERATIONS",
        title="Unverified latency",
        service="checkout-service",
        severity="high",
    )
    database.create_incident(incident)
    state = initial_state(incident.id, max_iterations=3)
    state["iteration_count"] = 3
    state["active_hypothesis"] = Hypothesis(
        title="Payment latency exceeds timeout budget",
        suspected_service="payment-service",
        suspected_failure_type=FailureType.PAYMENT_LATENCY,
        reasoning_summary="Candidate hypothesis",
        supporting_evidence_ids=["log:checkout:1"],
    )
    state["verification"] = VerificationResult(
        is_sufficient=False,
        evidence_support="Evidence is insufficient",
        supported_evidence_ids=[],
        unresolved_questions=["Need a paired payment duration"],
    )
    state["evidence"] = [
        EvidenceItem(
            id="log:checkout:1",
            kind=EvidenceKind.LOG,
            source="checkout-service",
            summary="Checkout returned 504",
            details={"request_id": "req-1", "status_code": 504, "duration_ms": 1015},
        )
    ]
    nodes = InvestigationNodes(database, settings)

    result = await nodes.generate_report(state)

    report = result["final_report"]
    assert report.root_cause.startswith("Unverified hypothesis:")
    assert any("Maximum investigation attempts" in item for item in report.limitations)
    assert any("insufficient" in item.lower() for item in report.limitations)
    assert database.get_incident(incident.id).status == IncidentStatus.RESOLVED
    assert database.get_report(incident.id) is not None
