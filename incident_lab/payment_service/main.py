from __future__ import annotations

import asyncio
import random
import time
from datetime import UTC, datetime

from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel, Field

from incident_lab.runtime.store import append_log, load_deployments, load_scenario

app = FastAPI(title="TraceLens payment-service", version="1.0.0")


class ChargeRequest(BaseModel):
    amount_cents: int = Field(gt=0)
    currency: str = "USD"


def version() -> str:
    return next(
        item["version"] for item in load_deployments() if item["service"] == "payment-service"
    )


def log_request(
    request_id: str,
    traffic_batch_id: str | None,
    started: float,
    status: int,
    error_type: str | None,
) -> None:
    append_log(
        "payment-service",
        {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": "ERROR" if status >= 500 else "INFO",
            "service": "payment-service",
            "request_id": request_id,
            "traffic_batch_id": traffic_batch_id,
            "event": "payment.charge.completed" if status < 500 else "payment.charge.failed",
            "duration_ms": round((time.perf_counter() - started) * 1000, 2),
            "status_code": status,
            "error_type": error_type,
            "deployment_version": version(),
            "message": error_type or "Charge authorized",
        },
    )


@app.post("/charge")
async def charge(
    payload: ChargeRequest,
    x_request_id: str = Header(default="missing"),
    x_traffic_batch_id: str | None = Header(default=None),
) -> dict:
    started = time.perf_counter()
    scenario = load_scenario()
    await asyncio.sleep(scenario["payment_latency_ms"] / 1000)
    if not scenario["configuration_valid"]:
        log_request(x_request_id, x_traffic_batch_id, started, 500, "ProviderConfigurationError")
        raise HTTPException(status_code=500, detail="Payment provider configuration is invalid")
    if scenario["connection_limit"] <= 0:
        log_request(x_request_id, x_traffic_batch_id, started, 503, "ConnectionPoolExhausted")
        raise HTTPException(status_code=503, detail="No provider connections available")
    if random.random() < scenario["payment_failure_rate"]:
        log_request(x_request_id, x_traffic_batch_id, started, 502, "ProviderDeclinedError")
        raise HTTPException(status_code=502, detail="Payment provider rejected the charge")
    log_request(x_request_id, x_traffic_batch_id, started, 200, None)
    return {"status": "authorized", "amount_cents": payload.amount_cents, "request_id": x_request_id}


@app.get("/health")
async def health() -> dict:
    scenario = load_scenario()
    degraded = not scenario["configuration_valid"] or scenario["connection_limit"] <= 0
    return {
        "service": "payment-service",
        "status": "degraded" if degraded else "healthy",
        "deployment_version": version(),
        "provider_configured": scenario["configuration_valid"],
        "available_connections": scenario["connection_limit"],
    }
