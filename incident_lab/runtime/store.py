from __future__ import annotations

import json
import os
import threading
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

ROOT = Path(__file__).resolve().parents[2]
RUNTIME_DIRECTORY = Path(os.getenv("RUNTIME_DIRECTORY", ROOT / "data" / "runtime"))
SCENARIO_PATH = RUNTIME_DIRECTORY / "scenario.json"
DEPLOYMENTS_PATH = RUNTIME_DIRECTORY / "deployments.json"
_lock = threading.RLock()
_postgres_pool: ConnectionPool | None = None
_postgres_pool_url: str | None = None
_postgres_initialized = False
_configured_database_url: str | None = None

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

POSTGRES_SCHEMA = """
CREATE TABLE IF NOT EXISTS lab_runtime_state (
    key TEXT PRIMARY KEY,
    value_json TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS lab_runtime_logs (
    id BIGSERIAL PRIMARY KEY,
    service TEXT NOT NULL,
    traffic_batch_id TEXT,
    timestamp TEXT NOT NULL,
    payload_json TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_lab_runtime_logs_batch
ON lab_runtime_logs(traffic_batch_id, id);
"""


def _now() -> str:
    return datetime.now(UTC).isoformat()


def runtime_storage_backend(database_url: str | None = None) -> str:
    url = (
        database_url
        if database_url is not None
        else _configured_database_url or os.getenv("DATABASE_URL", "")
    )
    return "postgres" if url.startswith(("postgresql://", "postgres://")) else "file"


def configure_runtime(directory: Path, database_url: str | None = None) -> None:
    """Apply Pydantic/.env runtime configuration after process startup."""
    global RUNTIME_DIRECTORY, SCENARIO_PATH, DEPLOYMENTS_PATH, _configured_database_url
    RUNTIME_DIRECTORY = directory
    SCENARIO_PATH = directory / "scenario.json"
    DEPLOYMENTS_PATH = directory / "deployments.json"
    _configured_database_url = database_url


def _default_deployments() -> list[dict[str, Any]]:
    return [
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
    ]


def _pool() -> ConnectionPool:
    global _postgres_pool, _postgres_pool_url, _postgres_initialized
    url = _configured_database_url or os.getenv("DATABASE_URL", "")
    if not url.startswith(("postgresql://", "postgres://")):
        raise RuntimeError("Postgres Incident Lab storage requires DATABASE_URL")
    url = url.replace("postgres://", "postgresql://", 1)
    if _postgres_pool is None or _postgres_pool_url != url:
        if _postgres_pool is not None:
            _postgres_pool.close()
        _postgres_pool = ConnectionPool(
            conninfo=url,
            min_size=1,
            max_size=5,
            open=False,
            kwargs={"row_factory": dict_row, "prepare_threshold": 0},
        )
        _postgres_pool.open(wait=True)
        _postgres_pool_url = url
        _postgres_initialized = False
    return _postgres_pool


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(value, indent=2), encoding="utf-8")
    temporary.replace(path)


def _write_state(key: str, value: Any) -> None:
    with _pool().connection() as connection:
        connection.execute(
            """INSERT INTO lab_runtime_state (key, value_json, updated_at)
            VALUES (%s, %s, %s)
            ON CONFLICT(key) DO UPDATE SET
            value_json=excluded.value_json, updated_at=excluded.updated_at""",
            (key, json.dumps(value), _now()),
        )


def _read_state(key: str) -> Any:
    with _pool().connection() as connection:
        row = connection.execute(
            "SELECT value_json FROM lab_runtime_state WHERE key = %s", (key,)
        ).fetchone()
    return json.loads(row["value_json"]) if row else None


def ensure_runtime() -> None:
    global _postgres_initialized
    if runtime_storage_backend() == "postgres":
        with _lock:
            if _postgres_initialized:
                return
            with _pool().connection() as connection:
                for statement in POSTGRES_SCHEMA.split(";"):
                    if statement.strip():
                        connection.execute(statement)
            if _read_state("scenario") is None:
                _write_state(
                    "scenario",
                    {
                        "name": "baseline",
                        "activated_at": _now(),
                        **SCENARIOS["baseline"],
                    },
                )
            if _read_state("deployments") is None:
                _write_state("deployments", _default_deployments())
            _postgres_initialized = True
        return

    RUNTIME_DIRECTORY.mkdir(parents=True, exist_ok=True)
    if not SCENARIO_PATH.exists():
        _write_json(
            SCENARIO_PATH,
            {"name": "baseline", "activated_at": _now(), **SCENARIOS["baseline"]},
        )
    if not DEPLOYMENTS_PATH.exists():
        _write_json(DEPLOYMENTS_PATH, _default_deployments())


def activate_scenario(name: str) -> dict[str, Any]:
    if name not in SCENARIOS:
        raise ValueError(f"Unknown scenario: {name}")
    ensure_runtime()
    with _lock:
        state = {"name": name, "activated_at": _now(), **SCENARIOS[name]}
        deployments = load_deployments()
        if name == "bad_deployment":
            deployments = [
                item for item in deployments if item["service"] != "payment-service"
            ]
            deployments.append(
                {
                    "service": "payment-service",
                    "version": "2.5.0",
                    "deployed_at": _now(),
                    "commit_sha": "badc0de",
                    "summary": "Rotate provider endpoint and credential mapping",
                }
            )
        elif any(
            item["service"] == "payment-service" and item["version"] == "2.5.0"
            for item in deployments
        ):
            deployments = [
                item for item in deployments if item["service"] != "payment-service"
            ]
            deployments.append(_default_deployments()[1])
        if runtime_storage_backend() == "postgres":
            _write_state("scenario", state)
            _write_state("deployments", deployments)
        else:
            _write_json(SCENARIO_PATH, state)
            _write_json(DEPLOYMENTS_PATH, deployments)
    return state


def load_scenario() -> dict[str, Any]:
    ensure_runtime()
    if runtime_storage_backend() == "postgres":
        return _read_state("scenario")
    return json.loads(SCENARIO_PATH.read_text(encoding="utf-8"))


def load_deployments() -> list[dict[str, Any]]:
    ensure_runtime()
    if runtime_storage_backend() == "postgres":
        return _read_state("deployments")
    return json.loads(DEPLOYMENTS_PATH.read_text(encoding="utf-8"))


def append_log(service: str, entry: dict[str, Any]) -> int:
    ensure_runtime()
    if runtime_storage_backend() == "postgres":
        with _pool().connection() as connection:
            row = connection.execute(
                """INSERT INTO lab_runtime_logs
                (service, traffic_batch_id, timestamp, payload_json)
                VALUES (%s, %s, %s, %s) RETURNING id""",
                (
                    service,
                    entry.get("traffic_batch_id"),
                    entry["timestamp"],
                    json.dumps(entry, separators=(",", ":")),
                ),
            ).fetchone()
        return int(row["id"])

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


def load_logs(service: str, limit: int = 250) -> list[dict[str, Any]]:
    ensure_runtime()
    if runtime_storage_backend() == "postgres":
        with _pool().connection() as connection:
            rows = connection.execute(
                """SELECT id, payload_json FROM lab_runtime_logs
                WHERE service = %s ORDER BY id DESC LIMIT %s""",
                (service, limit),
            ).fetchall()
        return [
            {"log_sequence": row["id"], **json.loads(row["payload_json"])}
            for row in reversed(rows)
        ]
    path = RUNTIME_DIRECTORY / f"{service}.jsonl"
    if not path.exists():
        return []
    entries: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines()[-limit:]:
        try:
            entries.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return entries


def clear_logs() -> None:
    ensure_runtime()
    if runtime_storage_backend() == "postgres":
        with _pool().connection() as connection:
            connection.execute("DELETE FROM lab_runtime_logs")
        return
    for service in ("checkout-service", "payment-service"):
        path = RUNTIME_DIRECTORY / f"{service}.jsonl"
        if path.exists():
            path.unlink()


def close_runtime_storage() -> None:
    global _postgres_pool, _postgres_pool_url, _postgres_initialized
    if _postgres_pool is not None:
        _postgres_pool.close()
    _postgres_pool = None
    _postgres_pool_url = None
    _postgres_initialized = False
