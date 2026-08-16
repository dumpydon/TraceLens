from __future__ import annotations

import asyncio
import uuid
from collections.abc import AsyncIterator
from datetime import UTC, datetime

import httpx
from fastapi import APIRouter, BackgroundTasks, HTTPException, Query, Request, status
from fastapi.responses import StreamingResponse
from incident_lab.runtime.store import SCENARIOS, activate_scenario, clear_logs, load_scenario

from app.api.schemas import (
    IncidentCreate,
    IncidentPublic,
    InvestigationAccepted,
    OverviewResponse,
    TrafficGenerationResponse,
)
from app.core.config import get_settings
from app.core.database import Database
from app.domain.models import Incident, IncidentStatus, Scenario, TrafficBatch
from app.services.investigation import load_checkpoint_state, run_investigation

router = APIRouter(prefix="/api")


def database() -> Database:
    return Database()


def public_incident(incident: Incident) -> IncidentPublic:
    return IncidentPublic.model_validate(incident.model_dump(exclude={"scenario_label"}))


@router.get("/overview", response_model=OverviewResponse)
async def overview() -> OverviewResponse:
    db = database()
    incidents = db.list_incidents()
    evaluations = db.list_evaluations()
    latest_score = None
    if evaluations:
        item = evaluations[0]
        latest_score = round(
            (
                item.root_cause_correctness
                + item.affected_service_correctness
                + item.retrieval_relevance
                + item.evidence_groundedness
            )
            / 4,
            3,
        )
    return OverviewResponse(
        active_incidents=sum(item.status == IncidentStatus.INVESTIGATING for item in incidents),
        resolved_incidents=sum(item.status == IncidentStatus.RESOLVED for item in incidents),
        recent_incidents=[public_incident(item) for item in incidents[:5]],
        latest_evaluation_score=latest_score,
    )


@router.get("/incidents", response_model=list[IncidentPublic])
async def list_incidents() -> list[IncidentPublic]:
    return [public_incident(item) for item in database().list_incidents()]


@router.post("/incidents", response_model=IncidentPublic, status_code=status.HTTP_201_CREATED)
async def create_incident(payload: IncidentCreate) -> IncidentPublic:
    db = database()
    if payload.traffic_batch_id is not None:
        batch = db.get_traffic_batch(payload.traffic_batch_id)
        if not batch:
            raise HTTPException(status_code=404, detail="Traffic batch not found")
    else:
        batch = db.latest_traffic_batch()
    incident = Incident(
        id=f"INC-{uuid.uuid4().hex[:8].upper()}",
        **payload.model_dump(exclude={"traffic_batch_id"}),
        traffic_batch_id=batch.id if batch else None,
        observation_started_at=batch.started_at if batch else None,
        observation_ended_at=batch.ended_at if batch else None,
    )
    db.create_incident(incident)
    return public_incident(incident)


@router.get("/incidents/{incident_id}", response_model=IncidentPublic)
async def get_incident(incident_id: str) -> IncidentPublic:
    incident = database().get_incident(incident_id)
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    return public_incident(incident)


@router.post(
    "/incidents/{incident_id}/investigate",
    response_model=InvestigationAccepted,
    status_code=status.HTTP_202_ACCEPTED,
)
async def investigate_incident(incident_id: str, background_tasks: BackgroundTasks) -> InvestigationAccepted:
    db = database()
    incident = db.get_incident(incident_id)
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    if incident.status == IncidentStatus.INVESTIGATING:
        raise HTTPException(status_code=409, detail="Investigation is already running or can be resumed")
    if incident.status == IncidentStatus.RESOLVED:
        raise HTTPException(status_code=409, detail="Incident already has a completed report")
    background_tasks.add_task(run_investigation, incident_id, database=db)
    return InvestigationAccepted(
        incident_id=incident_id,
        status="accepted",
        events_url=f"/api/incidents/{incident_id}/events",
    )


@router.post("/incidents/{incident_id}/resume", response_model=InvestigationAccepted)
async def resume_investigation(incident_id: str, background_tasks: BackgroundTasks) -> InvestigationAccepted:
    incident = database().get_incident(incident_id)
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    if incident.status == IncidentStatus.RESOLVED:
        raise HTTPException(status_code=409, detail="Investigation is already complete")
    background_tasks.add_task(run_investigation, incident_id, resume=True)
    return InvestigationAccepted(
        incident_id=incident_id,
        status="resuming",
        events_url=f"/api/incidents/{incident_id}/events",
    )


@router.get("/incidents/{incident_id}/events")
async def stream_events(
    incident_id: str,
    request: Request,
    after: int = Query(default=0, ge=0),
) -> StreamingResponse:
    if not database().get_incident(incident_id):
        raise HTTPException(status_code=404, detail="Incident not found")

    async def event_stream() -> AsyncIterator[str]:
        cursor = after
        idle_ticks = 0
        while not await request.is_disconnected():
            events = database().list_events(incident_id, cursor)
            if events:
                idle_ticks = 0
                for event in events:
                    cursor = event.id or cursor
                    yield (
                        f"id: {cursor}\n"
                        f"event: {event.event_type.value}\n"
                        f"data: {event.model_dump_json()}\n\n"
                    )
                    if event.event_type.value in {"investigation_completed", "investigation_failed"}:
                        return
            else:
                idle_ticks += 1
                if idle_ticks % 30 == 0:
                    yield ": keep-alive\n\n"
            await asyncio.sleep(0.35)

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/incidents/{incident_id}/report")
async def get_report(incident_id: str):
    report = database().get_report(incident_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not available")
    return report


@router.get("/incidents/{incident_id}/evidence")
async def get_evidence(incident_id: str):
    if not database().get_incident(incident_id):
        raise HTTPException(status_code=404, detail="Incident not found")
    state = await load_checkpoint_state(incident_id)
    return state.get("evidence", [])


@router.get("/lab/scenarios", response_model=list[Scenario])
async def list_scenarios() -> list[Scenario]:
    active = load_scenario()["name"]
    return [
        Scenario(
            name=name,
            description=value["description"],
            expected_behavior=value["expected_behavior"],
            active=name == active,
        )
        for name, value in SCENARIOS.items()
    ]


@router.post("/lab/scenarios/{name}/activate")
async def activate_lab_scenario(name: str):
    try:
        state = activate_scenario(name)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"name": state["name"], "activated_at": state["activated_at"]}


@router.post("/lab/reset")
async def reset_lab():
    clear_logs()
    state = activate_scenario("baseline")
    return {"name": state["name"], "activated_at": state["activated_at"], "logs_cleared": True}


@router.post("/lab/traffic", response_model=TrafficGenerationResponse)
async def generate_lab_traffic(count: int = Query(default=12, ge=1, le=100)):
    settings = get_settings()
    batch_id = f"BATCH-{uuid.uuid4().hex[:12].upper()}"
    started_at = datetime.now(UTC)
    results: dict[str, int] = {}
    async with httpx.AsyncClient(timeout=3.0) as client:
        for _ in range(count):
            try:
                response = await client.post(
                    f"{settings.checkout_service_url}/checkout",
                    json={"amount_cents": 4999, "currency": "USD"},
                    headers={
                        "X-Request-ID": str(uuid.uuid4()),
                        "X-Traffic-Batch-ID": batch_id,
                    },
                )
                key = str(response.status_code)
            except httpx.RequestError:
                key = "connection_error"
            results[key] = results.get(key, 0) + 1
    ended_at = datetime.now(UTC)
    database().save_traffic_batch(
        TrafficBatch(
            id=batch_id,
            started_at=started_at,
            ended_at=ended_at,
            request_count=count,
            results=results,
        )
    )
    return {
        "traffic_batch_id": batch_id,
        "started_at": started_at,
        "ended_at": ended_at,
        "requests": count,
        "results": results,
    }


@router.get("/lab/health")
async def lab_health():
    settings = get_settings()
    result = []
    async with httpx.AsyncClient(timeout=1.5) as client:
        for service, url in (
            ("checkout-service", settings.checkout_service_url),
            ("payment-service", settings.payment_service_url),
        ):
            try:
                response = await client.get(f"{url}/health")
                result.append({"service": service, **response.json()})
            except (httpx.RequestError, ValueError):
                result.append({"service": service, "status": "offline"})
    return result


@router.get("/evaluations")
async def evaluations():
    return database().list_evaluations()
