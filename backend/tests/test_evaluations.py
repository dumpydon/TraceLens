from evaluation.run_eval import build_case_result
from fastapi.testclient import TestClient

from app.api import routes
from app.api.schemas import EvaluationRunStatus
from app.domain.models import EvaluationCaseResult, EvaluationSummary
from app.main import app


def case_result() -> EvaluationCaseResult:
    return EvaluationCaseResult(
        case_name="payment_latency",
        expected_root_cause_category="payment_latency",
        predicted_root_cause_category="payment_latency",
        expected_affected_service="payment-service",
        predicted_affected_service="payment-service",
        expected_evidence=["UpstreamPaymentTimeout"],
        retrieved_failure_types=["payment_latency"],
        retrieved_evidence_ids=["runbook:payment-latency"],
        citation_ids=["log:checkout:1"],
        available_evidence_ids=["log:checkout:1"],
        root_cause_correctness=1.0,
        affected_service_correctness=1.0,
        retrieval_relevance=1.0,
        evidence_groundedness=1.0,
    )


def evaluation_summary() -> EvaluationSummary:
    return EvaluationSummary(
        id="eval-test",
        examples=1,
        root_cause_correctness=1.0,
        affected_service_correctness=1.0,
        retrieval_relevance=1.0,
        evidence_groundedness=1.0,
        case_results=[case_result()],
    )


def test_case_results_round_trip_in_existing_summary_json(database):
    database.save_evaluation(evaluation_summary())

    stored = database.list_evaluations()[0]

    assert stored.case_results == [case_result()]


def test_legacy_summary_without_case_results_remains_compatible():
    summary = EvaluationSummary.model_validate(
        {
            "id": "eval-legacy",
            "examples": 5,
            "root_cause_correctness": 1.0,
            "affected_service_correctness": 1.0,
            "retrieval_relevance": 0.8,
            "evidence_groundedness": 1.0,
        }
    )

    assert summary.case_results == []


def test_case_result_uses_real_deterministic_evaluators():
    result = build_case_result(
        {
            "scenario": "payment_latency",
            "expected_root_cause_category": "payment_latency",
            "expected_affected_service": "payment-service",
            "important_expected_evidence": ["UpstreamPaymentTimeout"],
        },
        {
            "root_cause_category": "payment_latency",
            "affected_service": "payment-service",
            "retrieved_failure_types": ["payment_latency"],
            "retrieved_evidence_ids": ["runbook:payment-latency"],
            "citation_ids": ["log:checkout:1"],
            "available_evidence_ids": ["log:checkout:1"],
        },
    )

    assert result.root_cause_correctness == 1.0
    assert result.affected_service_correctness == 1.0
    assert result.retrieval_relevance == 1.0
    assert result.evidence_groundedness == 1.0


def test_evaluation_api_returns_persisted_case_results(database, monkeypatch):
    database.save_evaluation(evaluation_summary())
    monkeypatch.setattr(routes, "database", lambda: database)

    with TestClient(app) as client:
        response = client.get("/api/evaluations")

    assert response.status_code == 200
    assert response.json()[0]["case_results"][0]["case_name"] == "payment_latency"


def test_explicit_run_endpoint_launches_existing_benchmark(database, monkeypatch):
    summary = evaluation_summary()

    async def fake_run() -> EvaluationSummary:
        await database.asave_evaluation(summary)
        return summary

    monkeypatch.setattr(routes, "database", lambda: database)
    monkeypatch.setattr(routes, "run_evaluation_benchmark", fake_run)
    monkeypatch.setattr(routes, "evaluation_run_status", EvaluationRunStatus())

    with TestClient(app) as client:
        response = client.post("/api/evaluations/run")
        status = client.get("/api/evaluations/status")

    assert response.status_code == 202
    assert response.json()["status"] == "running"
    assert status.json() == {"status": "completed", "run_id": summary.id, "error": None}
    assert database.list_evaluations()[0].id == summary.id


def test_run_endpoint_rejects_concurrent_benchmark(monkeypatch):
    monkeypatch.setattr(
        routes,
        "evaluation_run_status",
        EvaluationRunStatus(status="running"),
    )

    with TestClient(app) as client:
        response = client.post("/api/evaluations/run")

    assert response.status_code == 409
    assert response.json() == {"detail": "An evaluation run is already in progress"}
