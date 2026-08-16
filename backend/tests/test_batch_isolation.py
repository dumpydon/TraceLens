import json
from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient

from app.api import routes
from app.domain.models import ServiceHealth, TrafficBatch
from app.graph.nodes import InvestigationNodes
from app.graph.state import initial_state
from app.main import app


def log_payload(
    sequence: int,
    *,
    service: str,
    request_id: str,
    batch_id: str,
    timestamp: datetime,
    duration_ms: float,
    status_code: int,
    error_type: str | None,
) -> dict:
    return {
        "log_sequence": sequence,
        "timestamp": timestamp.isoformat(),
        "level": "ERROR" if status_code >= 500 else "INFO",
        "service": service,
        "request_id": request_id,
        "traffic_batch_id": batch_id,
        "event": "request.completed" if status_code < 500 else "request.failed",
        "duration_ms": duration_ms,
        "status_code": status_code,
        "error_type": error_type,
        "deployment_version": "test",
    }


async def test_connection_exhaustion_then_latency_without_reset_is_isolated(
    settings, database, monkeypatch
):
    settings.runtime_directory.mkdir(parents=True)
    base = datetime(2026, 8, 15, 10, 0, tzinfo=UTC)
    old_batch = "BATCH-CONNECTION"
    latency_batch = "BATCH-LATENCY"
    checkout_logs = [
        log_payload(
            1,
            service="checkout-service",
            request_id="old-1",
            batch_id=old_batch,
            timestamp=base,
            duration_ms=80,
            status_code=502,
            error_type="UpstreamPaymentHTTP503",
        )
    ]
    payment_logs = [
        log_payload(
            1,
            service="payment-service",
            request_id="old-1",
            batch_id=old_batch,
            timestamp=base,
            duration_ms=80,
            status_code=503,
            error_type="ConnectionPoolExhausted",
        )
    ]
    for index in range(2):
        request_id = f"latency-{index}"
        timestamp = base + timedelta(minutes=1, seconds=index)
        checkout_logs.append(
            log_payload(
                index + 2,
                service="checkout-service",
                request_id=request_id,
                batch_id=latency_batch,
                timestamp=timestamp,
                duration_ms=1010,
                status_code=504,
                error_type="UpstreamPaymentTimeout",
            )
        )
        payment_logs.append(
            log_payload(
                index + 2,
                service="payment-service",
                request_id=request_id,
                batch_id=latency_batch,
                timestamp=timestamp + timedelta(milliseconds=800),
                duration_ms=1800,
                status_code=200,
                error_type=None,
            )
        )
    for service, entries in (
        ("checkout-service", checkout_logs),
        ("payment-service", payment_logs),
    ):
        (settings.runtime_directory / f"{service}.jsonl").write_text(
            "\n".join(json.dumps(item) for item in entries) + "\n",
            encoding="utf-8",
        )

    async def healthy_services(_settings):
        return [
            ServiceHealth(
                evidence_id=f"health:{service}:1",
                service=service,
                status="healthy",
                checked_at=base + timedelta(minutes=2),
                latency_ms=2,
            )
            for service in ("checkout-service", "payment-service")
        ]

    monkeypatch.setattr("app.graph.nodes.collect_health", healthy_services)
    database.save_traffic_batch(
        TrafficBatch(
            id=old_batch,
            started_at=base,
            ended_at=base + timedelta(seconds=1),
            request_count=1,
            results={"502": 1},
        )
    )
    database.save_traffic_batch(
        TrafficBatch(
            id=latency_batch,
            started_at=base + timedelta(minutes=1),
            ended_at=base + timedelta(minutes=2),
            request_count=2,
            results={"504": 2},
        )
    )
    monkeypatch.setattr(routes, "database", lambda: database)
    with TestClient(app) as client:
        response = client.post("/api/incidents", json={"traffic_batch_id": latency_batch})
    assert response.status_code == 201
    incident = database.get_incident(response.json()["id"])
    assert incident is not None
    assert incident.traffic_batch_id == latency_batch

    state = initial_state(incident.id)
    state["incident"] = incident
    nodes = InvestigationNodes(database, settings)

    state.update(await nodes.collect_runtime_context(state))
    assert {log.traffic_batch_id for log in state["logs"]} == {latency_batch}
    assert all(log.request_id != "old-1" for log in state["logs"])
    assert not any(item.id.endswith(":1") and item.kind.value == "log" for item in state["evidence"])

    analysis = nodes._fallback_analysis(state)
    state["runtime_analysis"] = analysis
    state["retrieved_documents"] = []
    hypothesis = nodes._fallback_hypothesis(state)
    state["active_hypothesis"] = hypothesis
    verification = nodes._fallback_verification(state)

    assert hypothesis.suspected_failure_type == "payment_latency"
    assert verification.is_sufficient is True
    assert "ConnectionPoolExhausted" not in analysis.failure_signals
    assert not any(
        item.details.get("error_type") == "ConnectionPoolExhausted"
        for item in state["evidence"]
    )
    state["verification"] = verification
    report = nodes._fallback_report(state)
    assert report.root_cause_category == "payment_latency"
