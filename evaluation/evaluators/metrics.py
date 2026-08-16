from __future__ import annotations

from typing import Any


def root_cause_correctness(outputs: dict[str, Any], reference_outputs: dict[str, Any]) -> dict:
    return {
        "key": "root_cause_correctness",
        "score": float(
            outputs.get("root_cause_category")
            == reference_outputs.get("expected_root_cause_category")
        ),
    }


def affected_service_correctness(outputs: dict[str, Any], reference_outputs: dict[str, Any]) -> dict:
    return {
        "key": "affected_service_correctness",
        "score": float(
            outputs.get("affected_service")
            == reference_outputs.get("expected_affected_service")
        ),
    }


def retrieval_relevance(outputs: dict[str, Any], reference_outputs: dict[str, Any]) -> dict:
    expected = reference_outputs.get("expected_root_cause_category")
    failure_types = set(outputs.get("retrieved_failure_types", []))
    score = 1.0 if expected == "healthy" or expected in failure_types else 0.0
    return {"key": "retrieval_relevance", "score": score}


def evidence_groundedness(outputs: dict[str, Any], _: dict[str, Any]) -> dict:
    citations = set(outputs.get("citation_ids", []))
    available = set(outputs.get("available_evidence_ids", []))
    score = float(bool(citations) and citations.issubset(available))
    return {"key": "evidence_groundedness", "score": score}


EVALUATORS = [
    root_cause_correctness,
    affected_service_correctness,
    retrieval_relevance,
    evidence_groundedness,
]

