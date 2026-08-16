from __future__ import annotations

import asyncio
import os
import time
import uuid
from datetime import UTC, datetime

import httpx
from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel, Field

from incident_lab.runtime.store import append_log, load_deployments

app = FastAPI(title="TraceLens checkout-service", version="1.0.0")
_background_payment_tasks: set[asyncio.Task[httpx.Response]] = set()


class CheckoutRequest(BaseModel):
    amount_cents: int = Field(default=4999, gt=0)
    currency: str = "USD"


async def version() -> str:
    deployments = await asyncio.to_thread(load_deployments)
    return next(
        item["version"] for item in deployments if item["service"] == "checkout-service"
    )


async def write_log(
    request_id: str,
    traffic_batch_id: str | None,
    started: float,
    status: int,
    error_type: str | None,
) -> None:
    payload = {
        "timestamp": datetime.now(UTC).isoformat(),
        "level": "ERROR" if status >= 500 else "INFO",
        "service": "checkout-service",
        "request_id": request_id,
        "traffic_batch_id": traffic_batch_id,
        "event": "checkout.completed" if status < 500 else "checkout.failed",
        "duration_ms": round((time.perf_counter() - started) * 1000, 2),
        "status_code": status,
        "error_type": error_type,
        "deployment_version": await version(),
        "message": error_type or "Checkout completed",
    }
    await asyncio.to_thread(append_log, "checkout-service", payload)


async def request_payment(
    payload: CheckoutRequest, headers: dict[str, str]
) -> httpx.Response:
    if os.getenv("ENVIRONMENT", "development").lower() == "production":
        from incident_lab.payment_service.main import app as payment_app

        transport = httpx.ASGITransport(app=payment_app)
        async with httpx.AsyncClient(
            transport=transport, base_url="http://payment.internal"
        ) as client:
            return await client.post(
                "/charge", json=payload.model_dump(), headers=headers
            )
    payment_url = os.getenv("PAYMENT_SERVICE_URL", "http://127.0.0.1:8102")
    async with httpx.AsyncClient(timeout=1.0) as client:
        return await client.post(
            f"{payment_url}/charge", json=payload.model_dump(), headers=headers
        )


def _payment_task_finished(task: asyncio.Task[httpx.Response]) -> None:
    _background_payment_tasks.discard(task)
    if not task.cancelled():
        task.exception()


@app.post("/checkout")
async def checkout(
    payload: CheckoutRequest,
    x_request_id: str | None = Header(default=None),
    x_traffic_batch_id: str | None = Header(default=None),
) -> dict:
    request_id = x_request_id or str(uuid.uuid4())
    started = time.perf_counter()
    try:
        headers = {"X-Request-ID": request_id}
        if x_traffic_batch_id:
            headers["X-Traffic-Batch-ID"] = x_traffic_batch_id
        if os.getenv("ENVIRONMENT", "development").lower() == "production":
            payment_task = asyncio.create_task(request_payment(payload, headers))
            _background_payment_tasks.add(payment_task)
            payment_task.add_done_callback(_payment_task_finished)
            response = await asyncio.wait_for(asyncio.shield(payment_task), timeout=1.0)
        else:
            response = await request_payment(payload, headers)
        response.raise_for_status()
    except (TimeoutError, httpx.TimeoutException) as exc:
        await write_log(
            request_id, x_traffic_batch_id, started, 504, "UpstreamPaymentTimeout"
        )
        raise HTTPException(
            status_code=504, detail="Payment authorization timed out"
        ) from exc
    except httpx.HTTPStatusError as exc:
        error_type = f"UpstreamPaymentHTTP{exc.response.status_code}"
        await write_log(request_id, x_traffic_batch_id, started, 502, error_type)
        raise HTTPException(
            status_code=502, detail="Payment authorization failed"
        ) from exc
    except httpx.RequestError as exc:
        await write_log(
            request_id, x_traffic_batch_id, started, 503, "PaymentServiceUnavailable"
        )
        raise HTTPException(
            status_code=503, detail="Payment service unavailable"
        ) from exc
    await write_log(request_id, x_traffic_batch_id, started, 200, None)
    return {"status": "confirmed", "request_id": request_id}


@app.get("/health")
async def health() -> dict:
    return {
        "service": "checkout-service",
        "status": "healthy",
        "deployment_version": await version(),
    }
