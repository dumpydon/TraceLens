from datetime import timedelta

from fastapi.testclient import TestClient

from app.api import routes
from app.domain.models import TrafficBatch, utc_now
from app.main import app


def test_incident_endpoints_use_typed_public_schema(database, monkeypatch):
    monkeypatch.setattr(routes, "database", lambda: database)
    with TestClient(app) as client:
        response = client.post("/api/incidents", json={})
        assert response.status_code == 201
        payload = response.json()
        assert payload["id"].startswith("INC-")
        assert "scenario_label" not in payload
        listed = client.get("/api/incidents")
        assert listed.status_code == 200
        assert listed.json()[0]["id"] == payload["id"]


def test_health_endpoint():
    with TestClient(app) as client:
        assert client.get("/health").json()["status"] == "healthy"


def test_incident_binds_to_latest_completed_traffic_batch(database, monkeypatch):
    now = utc_now()
    database.save_traffic_batch(
        TrafficBatch(
            id="BATCH-NEWEST",
            started_at=now,
            ended_at=now,
            request_count=12,
            results={"504": 12},
        )
    )
    monkeypatch.setattr(routes, "database", lambda: database)
    with TestClient(app) as client:
        incident_id = client.post("/api/incidents", json={}).json()["id"]
    incident = database.get_incident(incident_id)
    assert incident.traffic_batch_id == "BATCH-NEWEST"
    assert incident.observation_started_at == now


def test_incident_binds_to_explicit_traffic_batch_instead_of_latest(database, monkeypatch):
    now = utc_now()
    explicit_batch = TrafficBatch(
        id="BATCH-PAYMENT-LATENCY",
        started_at=now,
        ended_at=now + timedelta(seconds=12),
        request_count=12,
        results={"504": 12},
    )
    latest_batch = TrafficBatch(
        id="BATCH-OTHER-LATEST",
        started_at=now + timedelta(minutes=1),
        ended_at=now + timedelta(minutes=1, seconds=1),
        request_count=12,
        results={"502": 12},
    )
    database.save_traffic_batch(explicit_batch)
    database.save_traffic_batch(latest_batch)
    monkeypatch.setattr(routes, "database", lambda: database)

    with TestClient(app) as client:
        response = client.post(
            "/api/incidents",
            json={"traffic_batch_id": explicit_batch.id},
        )

    assert response.status_code == 201
    incident = database.get_incident(response.json()["id"])
    assert incident.traffic_batch_id == explicit_batch.id
    assert incident.observation_started_at == explicit_batch.started_at
    assert incident.observation_ended_at == explicit_batch.ended_at


def test_incident_rejects_invalid_explicit_traffic_batch(database, monkeypatch):
    monkeypatch.setattr(routes, "database", lambda: database)

    with TestClient(app) as client:
        response = client.post(
            "/api/incidents",
            json={"traffic_batch_id": "BATCH-DOES-NOT-EXIST"},
        )

    assert response.status_code == 404
    assert response.json() == {"detail": "Traffic batch not found"}
    assert database.list_incidents() == []


def test_incident_rejects_empty_explicit_traffic_batch_instead_of_falling_back(
    database, monkeypatch
):
    now = utc_now()
    database.save_traffic_batch(
        TrafficBatch(
            id="BATCH-LATEST",
            started_at=now,
            ended_at=now,
            request_count=1,
            results={"200": 1},
        )
    )
    monkeypatch.setattr(routes, "database", lambda: database)

    with TestClient(app) as client:
        response = client.post("/api/incidents", json={"traffic_batch_id": ""})

    assert response.status_code == 404
    assert database.list_incidents() == []


def test_generate_traffic_returns_and_persists_its_exact_batch_id(database, monkeypatch):
    class FakeResponse:
        status_code = 504

    class FakeAsyncClient:
        def __init__(self, **_kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            return None

        async def post(self, *_args, **_kwargs):
            return FakeResponse()

    monkeypatch.setattr(routes, "database", lambda: database)
    monkeypatch.setattr(routes.httpx, "AsyncClient", FakeAsyncClient)

    with TestClient(app) as client:
        response = client.post("/api/lab/traffic?count=2")

    assert response.status_code == 200
    payload = response.json()
    assert payload["traffic_batch_id"].startswith("BATCH-")
    assert payload["requests"] == 2
    assert payload["results"] == {"504": 2}
    persisted = database.get_traffic_batch(payload["traffic_batch_id"])
    assert persisted is not None
    assert persisted.id == payload["traffic_batch_id"]
