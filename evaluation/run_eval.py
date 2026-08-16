from __future__ import annotations

import argparse
import asyncio
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.core.database import Database
from app.domain.models import EvaluationSummary, Incident, Severity, TrafficBatch
from app.services.investigation import load_checkpoint_state, run_investigation

from evaluation.evaluators.metrics import EVALUATORS
from incident_lab.runtime.store import activate_scenario, clear_logs
from incident_lab.scenarios.__main__ import generate_traffic

ROOT = Path(__file__).resolve().parents[1]


async def evaluate_example(
    example: dict[str, Any], traffic_count: int
) -> dict[str, float]:
    clear_logs()
    activate_scenario(example["scenario"])
    batch_id = f"BATCH-EVAL-{uuid.uuid4().hex[:8].upper()}"
    started_at = datetime.now(timezone.utc)
    traffic = await generate_traffic(traffic_count, "http://127.0.0.1:8101", batch_id)
    ended_at = datetime.now(timezone.utc)
    if traffic.get("connection_error"):
        raise RuntimeError(
            "Incident Lab services are not reachable; start both services before evaluation"
        )
    if example["scenario"] == "payment_latency":
        # Checkout times out before payment finishes; let the correlated server log land.
        await asyncio.sleep(1.0)
    database = Database()
    await database.asave_traffic_batch(
        TrafficBatch(
            id=batch_id,
            started_at=started_at,
            ended_at=ended_at,
            request_count=traffic_count,
            results=traffic,
        )
    )
    incident = Incident(
        id=f"EVAL-{uuid.uuid4().hex[:8].upper()}",
        title="Evaluation incident: checkout reliability",
        service="checkout-service",
        severity=Severity.HIGH,
        summary="A reproducible Incident Lab evaluation case.",
        traffic_batch_id=batch_id,
        observation_started_at=started_at,
        observation_ended_at=ended_at,
    )
    await database.acreate_incident(incident)
    await run_investigation(incident.id, database=database)
    report = await database.aget_report(incident.id)
    if not report:
        raise RuntimeError(f"No report produced for {incident.id}")
    state = await load_checkpoint_state(incident.id)
    retrieved = state.get("retrieved_documents", [])
    evidence = state.get("evidence", [])
    outputs = {
        "root_cause_category": report.root_cause_category,
        "affected_service": report.affected_service,
        "retrieved_failure_types": [
            item.failure_type for item in retrieved if item.failure_type
        ],
        "citation_ids": [item.evidence_id for item in report.evidence],
        "available_evidence_ids": [item.id for item in evidence],
    }
    return {
        item["key"]: item["score"]
        for evaluator in EVALUATORS
        if (item := evaluator(outputs, example))
    }


async def run(traffic_count: int = 6) -> EvaluationSummary:
    database = Database()
    await database.ainitialize()
    examples = json.loads(
        (ROOT / "evaluation" / "dataset" / "incidents.json").read_text()
    )
    scores = []
    for example in examples:
        result = await evaluate_example(example, traffic_count)
        scores.append(result)
        print(example["scenario"], json.dumps(result, sort_keys=True))
    summary = EvaluationSummary(
        id=f"eval-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}",
        examples=len(scores),
        root_cause_correctness=sum(item["root_cause_correctness"] for item in scores)
        / len(scores),
        affected_service_correctness=sum(
            item["affected_service_correctness"] for item in scores
        )
        / len(scores),
        retrieval_relevance=sum(item["retrieval_relevance"] for item in scores)
        / len(scores),
        evidence_groundedness=sum(item["evidence_groundedness"] for item in scores)
        / len(scores),
    )
    await database.asave_evaluation(summary)
    activate_scenario("baseline")
    print(summary.model_dump_json(indent=2))
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run the TraceLens offline evaluation dataset"
    )
    parser.add_argument("--traffic-count", type=int, default=6)
    args = parser.parse_args()
    asyncio.run(run(args.traffic_count))


if __name__ == "__main__":
    main()
