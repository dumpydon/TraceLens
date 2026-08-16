import asyncio

import httpx
from incident_lab.checkout_service.main import app as checkout_app
from incident_lab.runtime import store

from app.core.config import Settings
from app.core.database import Database
from app.main import create_app
from app.services.investigation import checkpoint_backend


def test_local_configuration_selects_sqlite_and_external_lab(tmp_path):
    settings = Settings(
        environment="development",
        database_url=f"sqlite:///{tmp_path / 'local.db'}",
    )

    assert settings.database_backend == "sqlite"
    assert Database(database_url=settings.database_url).backend == "sqlite"
    assert settings.embedded_incident_lab is False
    assert checkpoint_backend(settings) == "sqlite"


def test_production_configuration_selects_postgres_without_connecting():
    settings = Settings(
        environment="production",
        database_url="postgresql://user:password@pooler.example.test:5432/postgres",
    )

    assert settings.database_backend == "postgres"
    assert Database(database_url=settings.database_url).backend == "postgres"
    assert settings.embedded_incident_lab is True
    assert checkpoint_backend(settings) == "postgres"
    assert store.runtime_storage_backend(settings.database_url) == "postgres"


def test_production_app_mounts_both_incident_lab_services(tmp_path):
    settings = Settings(
        environment="production",
        database_url=f"sqlite:///{tmp_path / 'hosted.db'}",
        frontend_origin="https://tracelens.example.vercel.app/",
    )
    application = create_app(settings)
    paths = {route.path for route in application.routes if hasattr(route, "path")}

    assert "/_internal/lab/checkout" in paths
    assert "/_internal/lab/payment" in paths
    assert settings.cors_origins == [
        "http://127.0.0.1:3000",
        "http://localhost:3000",
        "https://tracelens.example.vercel.app",
    ]


async def test_cors_allows_configured_frontend_and_rejects_other_origins(tmp_path):
    settings = Settings(
        database_url=f"sqlite:///{tmp_path / 'cors.db'}",
        frontend_origin="https://tracelens.example.vercel.app",
    )
    application = create_app(settings)
    transport = httpx.ASGITransport(app=application)
    async with httpx.AsyncClient(transport=transport, base_url="http://api.internal") as client:
        allowed = await client.options(
            "/health",
            headers={
                "Origin": settings.frontend_origin,
                "Access-Control-Request-Method": "GET",
            },
        )
        rejected = await client.options(
            "/health",
            headers={
                "Origin": "https://untrusted.example",
                "Access-Control-Request-Method": "GET",
            },
        )

    assert allowed.headers["access-control-allow-origin"] == settings.frontend_origin
    assert "access-control-allow-origin" not in rejected.headers


async def test_hosted_payment_latency_keeps_late_payment_completion(tmp_path, monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "production")
    store.configure_runtime(tmp_path, f"sqlite:///{tmp_path / 'app.db'}")
    store.clear_logs()
    store.activate_scenario("payment_latency")

    transport = httpx.ASGITransport(app=checkout_app)
    async with httpx.AsyncClient(
        transport=transport, base_url="http://checkout.internal"
    ) as client:
        response = await client.post(
            "/checkout",
            json={"amount_cents": 4999, "currency": "USD"},
            headers={
                "X-Request-ID": "hosted-latency-request",
                "X-Traffic-Batch-ID": "BATCH-HOSTED-LATENCY",
            },
        )

    assert response.status_code == 504
    await asyncio.sleep(0.95)
    checkout_logs = store.load_logs("checkout-service")
    payment_logs = store.load_logs("payment-service")

    assert checkout_logs[-1]["error_type"] == "UpstreamPaymentTimeout"
    assert checkout_logs[-1]["duration_ms"] >= 950
    assert payment_logs[-1]["status_code"] == 200
    assert payment_logs[-1]["duration_ms"] >= 1750
    assert payment_logs[-1]["request_id"] == "hosted-latency-request"
    assert payment_logs[-1]["traffic_batch_id"] == "BATCH-HOSTED-LATENCY"
