from __future__ import annotations

import os
import time
import uuid
from datetime import UTC, datetime

import httpx
from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel, Field

from incident_lab.runtime.store import append_log, load_deployments

app = FastAPI(title="TraceLens checkout-service", version="1.0.0")
PAYMENT_URL = os.getenv("PAYMENT_SERVICE_URL", "http://127.0.0.1:8102")


class CheckoutRequest(BaseModel):
    amount_cents: int = Field(default=4999, gt=0)
    currency: str = "USD"


def version() -> str:
    return next(
        item["version"] for item in load_deployments() if item["service"] == "checkout-service"
    )


def write_log(
    request_id: str,
    traffic_batch_id: str | None,
    started: float,
    status: int,
    error_type: str | None,
) -> None:
    append_log(
        "checkout-service",
        {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": "ERROR" if status >= 500 else "INFO",
            "service": "checkout-service",
            "request_id": request_id,
            "traffic_batch_id": traffic_batch_id,
            "event": "checkout.completed" if status < 500 else "checkout.failed",
            "duration_ms": round((time.perf_counter() - started) * 1000, 2),
            "status_code": status,
            "error_type": error_type,
            "deployment_version": version(),
            "message": error_type or "Checkout completed",
        },
    )


@app.post("/checkout")
async def checkout(
    payload: CheckoutRequest,
    x_request_id: str | None = Header(default=None),
    x_traffic_batch_id: str | None = Header(default=None),
) -> dict:
    request_id = x_request_id or str(uuid.uuid4())
    started = time.perf_counter()
    try:
        async with httpx.AsyncClient(timeout=1.0) as client:
            headers = {"X-Request-ID": request_id}
            if x_traffic_batch_id:
                headers["X-Traffic-Batch-ID"] = x_traffic_batch_id
            response = await client.post(
                f"{PAYMENT_URL}/charge",
                json=payload.model_dump(),
                headers=headers,
            )
            response.raise_for_status()
    except httpx.TimeoutException as exc:
        write_log(request_id, x_traffic_batch_id, started, 504, "UpstreamPaymentTimeout")
        raise HTTPException(status_code=504, detail="Payment authorization timed out") from exc
    except httpx.HTTPStatusError as exc:
        error_type = f"UpstreamPaymentHTTP{exc.response.status_code}"
        write_log(request_id, x_traffic_batch_id, started, 502, error_type)
        raise HTTPException(status_code=502, detail="Payment authorization failed") from exc
    except httpx.RequestError as exc:
        write_log(request_id, x_traffic_batch_id, started, 503, "PaymentServiceUnavailable")
        raise HTTPException(status_code=503, detail="Payment service unavailable") from exc
    write_log(request_id, x_traffic_batch_id, started, 200, None)
    return {"status": "confirmed", "request_id": request_id}


@app.get("/health")
async def health() -> dict:
    return {"service": "checkout-service", "status": "healthy", "deployment_version": version()}
