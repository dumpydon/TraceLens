from __future__ import annotations

import json
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

from app.core.config import get_settings
from app.domain.models import (
    EvaluationSummary,
    Incident,
    IncidentStatus,
    InvestigationEvent,
    RootCauseReport,
    TrafficBatch,
)

SCHEMA = """
PRAGMA journal_mode=WAL;
CREATE TABLE IF NOT EXISTS incidents (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    service TEXT NOT NULL,
    severity TEXT NOT NULL,
    status TEXT NOT NULL,
    started_at TEXT NOT NULL,
    scenario_label TEXT,
    summary TEXT NOT NULL DEFAULT '',
    traffic_batch_id TEXT,
    observation_started_at TEXT,
    observation_ended_at TEXT
);
CREATE TABLE IF NOT EXISTS traffic_batches (
    id TEXT PRIMARY KEY,
    started_at TEXT NOT NULL,
    ended_at TEXT NOT NULL,
    request_count INTEGER NOT NULL,
    results_json TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS investigation_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    incident_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    stage TEXT NOT NULL,
    summary TEXT NOT NULL,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    FOREIGN KEY (incident_id) REFERENCES incidents(id)
);
CREATE INDEX IF NOT EXISTS idx_events_incident ON investigation_events(incident_id, id);
CREATE TABLE IF NOT EXISTS reports (
    incident_id TEXT PRIMARY KEY,
    report_json TEXT NOT NULL,
    generated_at TEXT NOT NULL,
    FOREIGN KEY (incident_id) REFERENCES incidents(id)
);
CREATE TABLE IF NOT EXISTS evaluation_summaries (
    id TEXT PRIMARY KEY,
    created_at TEXT NOT NULL,
    summary_json TEXT NOT NULL
);
"""


class Database:
    def __init__(self, path: Path | None = None):
        self.path = path or get_settings().database_path
        self.path.parent.mkdir(parents=True, exist_ok=True)

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.path, timeout=15)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys=ON")
        try:
            yield connection
            connection.commit()
        finally:
            connection.close()

    def initialize(self) -> None:
        with self.connect() as connection:
            connection.executescript(SCHEMA)
            columns = {
                row["name"] for row in connection.execute("PRAGMA table_info(incidents)").fetchall()
            }
            for name, sql_type in (
                ("traffic_batch_id", "TEXT"),
                ("observation_started_at", "TEXT"),
                ("observation_ended_at", "TEXT"),
            ):
                if name not in columns:
                    connection.execute(f"ALTER TABLE incidents ADD COLUMN {name} {sql_type}")

    def create_incident(self, incident: Incident) -> Incident:
        with self.connect() as connection:
            connection.execute(
                """INSERT INTO incidents
                (id, title, service, severity, status, started_at, scenario_label, summary,
                 traffic_batch_id, observation_started_at, observation_ended_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    incident.id,
                    incident.title,
                    incident.service,
                    incident.severity.value,
                    incident.status.value,
                    incident.started_at.isoformat(),
                    incident.scenario_label,
                    incident.summary,
                    incident.traffic_batch_id,
                    incident.observation_started_at.isoformat()
                    if incident.observation_started_at
                    else None,
                    incident.observation_ended_at.isoformat()
                    if incident.observation_ended_at
                    else None,
                ),
            )
        return incident

    def save_traffic_batch(self, batch: TrafficBatch) -> TrafficBatch:
        with self.connect() as connection:
            connection.execute(
                """INSERT INTO traffic_batches
                (id, started_at, ended_at, request_count, results_json)
                VALUES (?, ?, ?, ?, ?)""",
                (
                    batch.id,
                    batch.started_at.isoformat(),
                    batch.ended_at.isoformat(),
                    batch.request_count,
                    json.dumps(batch.results),
                ),
            )
        return batch

    def get_traffic_batch(self, batch_id: str) -> TrafficBatch | None:
        with self.connect() as connection:
            row = connection.execute(
                "SELECT * FROM traffic_batches WHERE id = ?", (batch_id,)
            ).fetchone()
        return self._traffic_batch(row) if row else None

    def latest_traffic_batch(self) -> TrafficBatch | None:
        with self.connect() as connection:
            row = connection.execute(
                "SELECT * FROM traffic_batches ORDER BY ended_at DESC LIMIT 1"
            ).fetchone()
        return self._traffic_batch(row) if row else None

    def list_incidents(self) -> list[Incident]:
        with self.connect() as connection:
            rows = connection.execute("SELECT * FROM incidents ORDER BY started_at DESC").fetchall()
        return [self._incident(row) for row in rows]

    def get_incident(self, incident_id: str) -> Incident | None:
        with self.connect() as connection:
            row = connection.execute("SELECT * FROM incidents WHERE id = ?", (incident_id,)).fetchone()
        return self._incident(row) if row else None

    def update_incident_status(self, incident_id: str, status: IncidentStatus) -> None:
        with self.connect() as connection:
            connection.execute(
                "UPDATE incidents SET status = ? WHERE id = ?", (status.value, incident_id)
            )

    def add_event(self, event: InvestigationEvent) -> InvestigationEvent:
        with self.connect() as connection:
            cursor = connection.execute(
                """INSERT INTO investigation_events
                (incident_id, event_type, timestamp, stage, summary, metadata_json)
                VALUES (?, ?, ?, ?, ?, ?)""",
                (
                    event.incident_id,
                    event.event_type.value,
                    event.timestamp.isoformat(),
                    event.stage,
                    event.summary,
                    json.dumps(event.metadata),
                ),
            )
            event.id = cursor.lastrowid
        return event

    def list_events(self, incident_id: str, after_id: int = 0) -> list[InvestigationEvent]:
        with self.connect() as connection:
            rows = connection.execute(
                """SELECT * FROM investigation_events
                WHERE incident_id = ? AND id > ? ORDER BY id""",
                (incident_id, after_id),
            ).fetchall()
        return [
            InvestigationEvent(
                id=row["id"],
                incident_id=row["incident_id"],
                event_type=row["event_type"],
                timestamp=row["timestamp"],
                stage=row["stage"],
                summary=row["summary"],
                metadata=json.loads(row["metadata_json"]),
            )
            for row in rows
        ]

    def save_report(self, report: RootCauseReport) -> None:
        with self.connect() as connection:
            connection.execute(
                """INSERT INTO reports (incident_id, report_json, generated_at) VALUES (?, ?, ?)
                ON CONFLICT(incident_id) DO UPDATE SET
                report_json=excluded.report_json, generated_at=excluded.generated_at""",
                (report.incident_id, report.model_dump_json(), report.generated_at.isoformat()),
            )

    def get_report(self, incident_id: str) -> RootCauseReport | None:
        with self.connect() as connection:
            row = connection.execute(
                "SELECT report_json FROM reports WHERE incident_id = ?", (incident_id,)
            ).fetchone()
        return RootCauseReport.model_validate_json(row["report_json"]) if row else None

    def save_evaluation(self, summary: EvaluationSummary) -> None:
        with self.connect() as connection:
            connection.execute(
                """INSERT OR REPLACE INTO evaluation_summaries
                (id, created_at, summary_json) VALUES (?, ?, ?)""",
                (summary.id, summary.created_at.isoformat(), summary.model_dump_json()),
            )

    def list_evaluations(self) -> list[EvaluationSummary]:
        with self.connect() as connection:
            rows = connection.execute(
                "SELECT summary_json FROM evaluation_summaries ORDER BY created_at DESC"
            ).fetchall()
        return [EvaluationSummary.model_validate_json(row["summary_json"]) for row in rows]

    @staticmethod
    def _incident(row: sqlite3.Row) -> Incident:
        keys = set(row.keys())
        return Incident(
            id=row["id"],
            title=row["title"],
            service=row["service"],
            severity=row["severity"],
            status=row["status"],
            started_at=datetime.fromisoformat(row["started_at"]),
            scenario_label=row["scenario_label"],
            summary=row["summary"],
            traffic_batch_id=row["traffic_batch_id"] if "traffic_batch_id" in keys else None,
            observation_started_at=(
                datetime.fromisoformat(row["observation_started_at"])
                if "observation_started_at" in keys and row["observation_started_at"]
                else None
            ),
            observation_ended_at=(
                datetime.fromisoformat(row["observation_ended_at"])
                if "observation_ended_at" in keys and row["observation_ended_at"]
                else None
            ),
        )

    @staticmethod
    def _traffic_batch(row: sqlite3.Row) -> TrafficBatch:
        return TrafficBatch(
            id=row["id"],
            started_at=datetime.fromisoformat(row["started_at"]),
            ended_at=datetime.fromisoformat(row["ended_at"]),
            request_count=row["request_count"],
            results=json.loads(row["results_json"]),
        )
