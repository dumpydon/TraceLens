from contextlib import contextmanager
from unittest.mock import Mock

import httpx

from app.core.database import Database, get_database
from app.main import create_app


def application(settings, database):
    # Validate secrets through Pydantic rather than model_copy's unvalidated update.
    configured = type(settings)(**{
        **settings.model_dump(), "tracelens_keepalive_secret": "test-maintenance-token"
    })
    app = create_app(configured)
    app.dependency_overrides[get_database] = lambda: database
    return app


async def test_authenticated_heartbeat_queries_on_every_request_without_mutation(
    settings, database, monkeypatch
):
    statements = []
    original_connect = database.connect

    @contextmanager
    def traced_connect():
        with original_connect() as connection:
            connection.connection.set_trace_callback(statements.append)
            yield connection

    monkeypatch.setattr(database, "connect", traced_connect)
    app = application(settings, database)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app), base_url="http://test"
    ) as client:
        for _ in range(2):
            response = await client.post(
                "/internal/maintenance/heartbeat",
                headers={"Authorization": "Bearer test-maintenance-token"},
            )
            assert response.status_code == 200
            assert set(response.json()) == {"status", "database", "checked_at"}
            assert response.json()["status"] == "ok"
            assert response.json()["database"] == "sqlite"

    assert statements.count("SELECT 1 AS alive") == 2
    assert all(statement.startswith("SELECT") for statement in statements)
    with original_connect() as connection:
        for table in (
            "incidents", "traffic_batches", "investigation_events", "reports", "evaluation_summaries"
        ):
            assert connection.execute(f"SELECT COUNT(*) AS count FROM {table}").fetchone()["count"] == 0
    assert not settings.checkpoint_database_path.exists()


async def test_missing_wrong_or_non_bearer_token_never_queries(settings, database, monkeypatch):
    query = Mock()
    monkeypatch.setattr(database, "heartbeat", query)
    app = application(settings, database)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app), base_url="http://test"
    ) as client:
        for token in (None, "Bearer wrong", "Basic test-maintenance-token"):
            headers = {} if token is None else {"Authorization": token}
            response = await client.post("/internal/maintenance/heartbeat", headers=headers)
            assert response.status_code == 401
    query.assert_not_called()


async def test_unconfigured_heartbeat_fails_closed(settings, database, monkeypatch):
    settings.tracelens_keepalive_secret = None
    query = Mock()
    monkeypatch.setattr(database, "heartbeat", query)
    app = create_app(settings)
    app.dependency_overrides[get_database] = lambda: database
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app), base_url="http://test"
    ) as client:
        response = await client.post("/internal/maintenance/heartbeat")
    assert response.status_code == 503
    assert response.json() == {"detail": "Maintenance unavailable"}
    query.assert_not_called()


async def test_database_failure_is_generic_and_does_not_leak_credentials(
    settings, database, monkeypatch, caplog
):
    monkeypatch.setattr(database, "heartbeat", Mock(side_effect=RuntimeError("private-db-password")))
    app = application(settings, database)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app), base_url="http://test"
    ) as client:
        response = await client.post(
            "/internal/maintenance/heartbeat",
            headers={"Authorization": "Bearer test-maintenance-token"},
        )
    assert response.status_code == 503
    assert response.json() == {"detail": "Database unavailable"}
    assert "private-db-password" not in response.text + caplog.text
    assert database.list_incidents() == []


def test_postgres_heartbeat_executes_select_through_existing_pool(monkeypatch):
    database = Database(database_url="postgresql://test@pooler.test/postgres")
    connection = Mock()
    connection.execute.return_value.fetchone.return_value = {"alive": 1}

    @contextmanager
    def pooled_connection():
        yield connection

    pool = Mock()
    pool.connection = pooled_connection
    monkeypatch.setattr(database, "_postgres_pool", lambda: pool)
    database.heartbeat()
    connection.execute.assert_called_once_with("SELECT 1 AS alive", ())
    connection.commit.assert_called_once()


async def test_public_health_does_not_require_maintenance_auth_or_database(settings, database):
    app = application(settings, database)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app), base_url="http://test"
    ) as client:
        response = await client.get("/health")
    assert response.json() == {"status": "healthy", "service": "tracelens-api"}
