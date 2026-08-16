from __future__ import annotations

import json
import os
import threading
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
RUNTIME_DIRECTORY = Path(os.getenv("RUNTIME_DIRECTORY", ROOT / "data" / "runtime"))
SCENARIO_PATH = RUNTIME_DIRECTORY / "scenario.json"
DEPLOYMENTS_PATH = RUNTIME_DIRECTORY / "deployments.json"
_lock = threading.Lock()

SCENARIOS: dict[str, dict[str, Any]] = {
    "baseline": {
        "description": "Normal payment processing with low latency and successful charges.",
        "expected_behavior": "Checkout and payment remain healthy.",
        "payment_latency_ms": 35,
        "payment_failure_rate": 0.0,
        "configuration_valid": True,
        "connection_limit": 100,
    },
    "payment_latency": {
        "description": "Payment authorization is delayed beyond the checkout timeout budget.",
        "expected_behavior": "Payment is slow and checkout records upstream timeouts.",
        "payment_latency_ms": 1800,
        "payment_failure_rate": 0.0,
        "configuration_valid": True,
        "connection_limit": 100,
    },
    "payment_failure": {
        "description": "The payment provider rejects every charge request.",
        "expected_behavior": "Payment returns HTTP 502 and checkout propagates failure.",
        "payment_latency_ms": 35,
        "payment_failure_rate": 1.0,
        "configuration_valid": True,
        "connection_limit": 100,
    },
    "bad_deployment": {
        "description": "A payment deployment contains an invalid provider configuration.",
        "expected_behavior": "Payment returns configuration errors after a new deployment.",
        "payment_latency_ms": 20,
        "payment_failure_rate": 0.0,
        "configuration_valid": False,
        "connection_limit": 100,
    },
    "connection_exhaustion": {
        "description": "The payment service has no available provider connections.",
        "expected_behavior": "Payment fails with connection pool exhaustion.",
        "payment_latency_ms": 80,
        "payment_failure_rate": 0.0,
        "configuration_valid": True,
        "connection_limit": 0,
    },
}


def _now() -> str:
    return datetime.now(UTC).isoformat()


def ensure_runtime() -> None:
    RUNTIME_DIRECTORY.mkdir(parents=True, exist_ok=True)
    if not SCENARIO_PATH.exists():
        activate_scenario("baseline")
    if not DEPLOYMENTS_PATH.exists():
        _write_json(
            DEPLOYMENTS_PATH,
            [
                {
                    "service": "checkout-service",
                    "version": "1.3.0",
                    "deployed_at": "2026-08-12T09:30:00+00:00",
                    "commit_sha": "a91c2f7",
                    "summary": "Checkout request correlation and timeout handling",
                },
                {
                    "service": "payment-service",
                    "version": "2.4.1",
                    "deployed_at": "2026-08-12T10:05:00+00:00",
                    "commit_sha": "42d8b9e",
                    "summary": "Provider client connection management",
                },
            ],
        )


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(value, indent=2), encoding="utf-8")
    temporary.replace(path)


def activate_scenario(name: str) -> dict[str, Any]:
    if name not in SCENARIOS:
        raise ValueError(f"Unknown scenario: {name}")
    with _lock:
        state = {"name": name, "activated_at": _now(), **SCENARIOS[name]}
        _write_json(SCENARIO_PATH, state)
        if name == "bad_deployment":
            deployments = load_deployments()
            deployments = [item for item in deployments if item["service"] != "payment-service"]
            deployments.append(
                {
                    "service": "payment-service",
                    "version": "2.5.0",
                    "deployed_at": _now(),
                    "commit_sha": "badc0de",
                    "summary": "Rotate provider endpoint and credential mapping",
                }
            )
            _write_json(DEPLOYMENTS_PATH, deployments)
        elif DEPLOYMENTS_PATH.exists():
            deployments = load_deployments()
            if any(item["service"] == "payment-service" and item["version"] == "2.5.0" for item in deployments):
                deployments = [item for item in deployments if item["service"] != "payment-service"]
                deployments.append(
                    {
                        "service": "payment-service",
                        "version": "2.4.1",
                        "deployed_at": "2026-08-12T10:05:00+00:00",
                        "commit_sha": "42d8b9e",
                        "summary": "Provider client connection management",
                    }
                )
                _write_json(DEPLOYMENTS_PATH, deployments)
    return state


def load_scenario() -> dict[str, Any]:
    ensure_runtime()
    return json.loads(SCENARIO_PATH.read_text(encoding="utf-8"))


def load_deployments() -> list[dict[str, Any]]:
    if not DEPLOYMENTS_PATH.exists():
        ensure_runtime()
    return json.loads(DEPLOYMENTS_PATH.read_text(encoding="utf-8"))


def append_log(service: str, entry: dict[str, Any]) -> int:
    ensure_runtime()
    path = RUNTIME_DIRECTORY / f"{service}.jsonl"
    with _lock:
        line_number = 1
        if path.exists():
            with path.open("r", encoding="utf-8") as existing:
                line_number += sum(1 for _ in existing)
        payload = {"log_sequence": line_number, **entry}
        with path.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(payload, separators=(",", ":")) + "\n")
    return line_number


def clear_logs() -> None:
    for service in ("checkout-service", "payment-service"):
        path = RUNTIME_DIRECTORY / f"{service}.jsonl"
        if path.exists():
            path.unlink()

