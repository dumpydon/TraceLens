from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import httpx

from app.core.config import Settings


@asynccontextmanager
async def lab_client(
    service: str, settings: Settings, *, timeout: float
) -> AsyncIterator[httpx.AsyncClient]:
    """Use normal HTTP locally and mounted ASGI applications in hosted V1."""
    if settings.embedded_incident_lab:
        if service == "checkout-service":
            from incident_lab.checkout_service.main import app
        elif service == "payment-service":
            from incident_lab.payment_service.main import app
        else:
            raise ValueError(f"Unknown Incident Lab service: {service}")
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url=f"http://{service}.internal",
            timeout=timeout,
        ) as client:
            yield client
        return

    base_url = (
        settings.checkout_service_url
        if service == "checkout-service"
        else settings.payment_service_url
    )
    async with httpx.AsyncClient(base_url=base_url, timeout=timeout) as client:
        yield client
