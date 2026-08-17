from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.domain.models import IncidentStatus, Severity


class IncidentCreate(BaseModel):
    title: str = Field(default="Checkout reliability degradation", min_length=3, max_length=120)
    service: str = "checkout-service"
    severity: Severity = Severity.HIGH
    summary: str = "Elevated checkout failures observed in the Incident Lab."
    traffic_batch_id: str | None = None


class IncidentPublic(BaseModel):
    id: str
    title: str
    service: str
    severity: Severity
    status: IncidentStatus
    started_at: datetime
    summary: str


class InvestigationAccepted(BaseModel):
    incident_id: str
    status: str
    events_url: str


class TrafficGenerationResponse(BaseModel):
    traffic_batch_id: str
    started_at: datetime
    ended_at: datetime
    requests: int
    results: dict[str, int]


class OverviewResponse(BaseModel):
    active_incidents: int
    resolved_incidents: int
    recent_incidents: list[IncidentPublic]
    latest_evaluation_score: float | None


class EvaluationRunStatus(BaseModel):
    status: Literal["idle", "running", "completed", "failed"] = "idle"
    run_id: str | None = None
    error: str | None = None
