from __future__ import annotations

import json
import time
from datetime import UTC, datetime
from pathlib import Path

import httpx
from incident_lab.runtime import store as runtime_store

from app.core.config import Settings, get_settings
from app.domain.models import Deployment, LogEntry, ServiceHealth
from app.services.lab_client import lab_client


def read_logs(
    runtime_directory: Path,
    limit: int = 250,
    *,
    traffic_batch_id: str | None = None,
    observation_started_at: datetime | None = None,
    observation_ended_at: datetime | None = None,
) -> list[LogEntry]:
    entries: list[LogEntry] = []
    if runtime_store.runtime_storage_backend() == "postgres":
        sources = [
            (service, runtime_store.load_logs(service, limit))
            for service in ("checkout-service", "payment-service")
        ]
    else:
        sources = []
        for path in sorted(runtime_directory.glob("*-service.jsonl")):
            payloads = []
            for line in path.read_text(encoding="utf-8").splitlines()[-limit:]:
                try:
                    payloads.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
            sources.append((path.stem, payloads))
    for service, payloads in sources:
        for fallback_sequence, raw_payload in enumerate(payloads, start=1):
            try:
                payload = dict(raw_payload)
                sequence = payload.pop("log_sequence", fallback_sequence)
                entry = LogEntry(evidence_id=f"log:{service}:{sequence}", **payload)
                if traffic_batch_id is not None and entry.traffic_batch_id != traffic_batch_id:
                    continue
                if traffic_batch_id is None and observation_started_at:
                    if entry.timestamp < observation_started_at:
                        continue
                    if observation_ended_at and entry.timestamp > observation_ended_at:
                        continue
                entries.append(entry)
            except (ValueError, TypeError):
                continue
    return sorted(entries, key=lambda entry: entry.timestamp)[-limit:]


def read_deployments(runtime_directory: Path, *, as_of: datetime | None = None) -> list[Deployment]:
    if runtime_store.runtime_storage_backend() == "postgres":
        payload = runtime_store.load_deployments()
    else:
        path = runtime_directory / "deployments.json"
        if not path.exists():
            return []
        payload = json.loads(path.read_text(encoding="utf-8"))
    deployments = [
        Deployment(evidence_id=f"deployment:{item['service']}:{item['version']}", **item)
        for item in payload
    ]
    return [item for item in deployments if as_of is None or item.deployed_at <= as_of]


async def collect_health(settings: Settings | None = None) -> list[ServiceHealth]:
    settings = settings or get_settings()
    results: list[ServiceHealth] = []
    for service in ("checkout-service", "payment-service"):
        async with lab_client(service, settings, timeout=1.5) as client:
            started = time.perf_counter()
            checked_at = datetime.now(UTC)
            try:
                response = await client.get("/health")
                duration_ms = (time.perf_counter() - started) * 1000
                payload = response.json()
                details = ", ".join(
                    f"{key}={value}"
                    for key, value in payload.items()
                    if key not in {"service", "status", "deployment_version"}
                )
                results.append(
                    ServiceHealth(
                        evidence_id=f"health:{service}:{int(checked_at.timestamp())}",
                        service=service,
                        status=payload.get("status", "unknown"),
                        checked_at=checked_at,
                        latency_ms=round(duration_ms, 2),
                        details=details or None,
                        deployment_version=payload.get("deployment_version"),
                    )
                )
            except (httpx.RequestError, ValueError) as exc:
                results.append(
                    ServiceHealth(
                        evidence_id=f"health:{service}:{int(checked_at.timestamp())}",
                        service=service,
                        status="unreachable",
                        checked_at=checked_at,
                        latency_ms=round((time.perf_counter() - started) * 1000, 2),
                        details=type(exc).__name__,
                    )
                )
    return results
