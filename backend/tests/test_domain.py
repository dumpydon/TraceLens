import pytest
from pydantic import ValidationError

from app.domain.models import ReportEvidence, RootCauseReport


def test_report_requires_evidence():
    with pytest.raises(ValidationError):
        RootCauseReport(
            incident_id="INC-1",
            root_cause="Unknown",
            root_cause_category="unknown",
            affected_service="unknown",
            summary="No supported finding",
            confidence=0.2,
            evidence=[],
            recommended_actions=[],
            limitations=["No runtime evidence"],
        )


def test_report_loads_bounded_legacy_model_confidence():
    report = RootCauseReport(
        incident_id="INC-1",
        root_cause="Latency",
        root_cause_category="payment_latency",
        affected_service="payment-service",
        summary="Supported",
        confidence=0.8,
        evidence=[ReportEvidence(evidence_id="log:payment:1", claim="slow")],
        recommended_actions=[],
        limitations=[],
    )
    assert report.confidence == 0.8
