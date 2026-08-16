from __future__ import annotations

import json
import time
from datetime import UTC, datetime
from pathlib import Path

import httpx

from app.core.config import Settings, get_settings
from app.domain.models import Deployment, LogEntry, ServiceHealth


def read_logs(
    runtime_directory: Path,
    limit: int = 250,
    *,
    traffic_batch_id: str | None = None,
    observation_started_at: datetime | None = None,
    observation_ended_at: datetime | None = None,
) -> list[LogEntry]:
    entries: list[LogEntry] = []
    for path in sorted(runtime_directory.glob("*-service.jsonl")):
        service = path.stem
        lines = path.read_text(encoding="utf-8").splitlines()[-limit:]
        for fallback_sequence, line in enumerate(lines, start=1):
            try:
                payload = json.loads(line)
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
            except (json.JSONDecodeError, ValueError, TypeError):
                continue
    return sorted(entries, key=lambda entry: entry.timestamp)[-limit:]


def read_deployments(
    runtime_directory: Path, *, as_of: datetime | None = None
) -> list[Deployment]:
    path = runtime_directory / "deployments.json"
    if not path.exists():
        return []
    deployments = [
        Deployment(
            evidence_id=f"deployment:{item['service']}:{item['version']}", **item
        )
        for item in json.loads(path.read_text(encoding="utf-8"))
    ]
    return [item for item in deployments if as_of is None or item.deployed_at <= as_of]


async def collect_health(settings: Settings | None = None) -> list[ServiceHealth]:
    settings = settings or get_settings()
    services = {
        "checkout-service": settings.checkout_service_url,
        "payment-service": settings.payment_service_url,
    }
    results: list[ServiceHealth] = []
    async with httpx.AsyncClient(timeout=1.5) as client:
        for service, base_url in services.items():
            started = time.perf_counter()
            checked_at = datetime.now(UTC)
            try:
                response = await client.get(f"{base_url}/health")
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
