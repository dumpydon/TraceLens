from __future__ import annotations

import asyncio
import json
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime
from functools import lru_cache
from pathlib import Path
from typing import Any

from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

from app.core.config import get_settings
from app.domain.models import (
    EvaluationSummary,
    Incident,
    IncidentStatus,
    InvestigationEvent,
    RootCauseReport,
    TrafficBatch,
)

SQLITE_SCHEMA = """
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

POSTGRES_SCHEMA = """
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
    id BIGSERIAL PRIMARY KEY,
    incident_id TEXT NOT NULL REFERENCES incidents(id),
    event_type TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    stage TEXT NOT NULL,
    summary TEXT NOT NULL,
    metadata_json TEXT NOT NULL DEFAULT '{}'
);
CREATE INDEX IF NOT EXISTS idx_events_incident ON investigation_events(incident_id, id);
CREATE TABLE IF NOT EXISTS reports (
    incident_id TEXT PRIMARY KEY REFERENCES incidents(id),
    report_json TEXT NOT NULL,
    generated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS evaluation_summaries (
    id TEXT PRIMARY KEY,
    created_at TEXT NOT NULL,
    summary_json TEXT NOT NULL
);
"""


class _ConnectionAdapter:
    """Normalize the tiny SQL dialect surface used by the V1 repository."""

    def __init__(self, connection: Any, *, postgres: bool):
        self.connection = connection
        self.postgres = postgres

    def execute(self, sql: str, params: tuple[Any, ...] = ()):
        statement = sql.replace("?", "%s") if self.postgres else sql
        return self.connection.execute(statement, params)

    def executescript(self, script: str) -> None:
        if not self.postgres:
            self.connection.executescript(script)
            return
        for statement in script.split(";"):
            if statement.strip():
                self.connection.execute(statement)


class Database:
    def __init__(self, path: Path | None = None, *, database_url: str | None = None):
        if path is not None:
            database_url = f"sqlite:///{path}"
        self.database_url = database_url or get_settings().database_url
        self.backend = self._backend_for_url(self.database_url)
        self.path = self._sqlite_path(self.database_url) if self.backend == "sqlite" else None
        if self.path:
            self.path.parent.mkdir(parents=True, exist_ok=True)
        self._pool: ConnectionPool | None = None

    @staticmethod
    def _backend_for_url(database_url: str) -> str:
        if database_url.startswith("sqlite:///"):
            return "sqlite"
        if database_url.startswith(("postgresql://", "postgres://")):
            return "postgres"
        raise ValueError("DATABASE_URL must use sqlite:/// or postgresql://")

    @staticmethod
    def _sqlite_path(database_url: str) -> Path:
        return Path(database_url.removeprefix("sqlite:///")).expanduser().resolve()

    def _postgres_pool(self) -> ConnectionPool:
        if self._pool is None:
            connection_url = self.database_url.replace("postgres://", "postgresql://", 1)
            self._pool = ConnectionPool(
                conninfo=connection_url,
                min_size=1,
                max_size=5,
                open=False,
                kwargs={"row_factory": dict_row, "prepare_threshold": 0},
            )
            self._pool.open(wait=True)
        return self._pool

    @contextmanager
    def connect(self) -> Iterator[_ConnectionAdapter]:
        if self.backend == "sqlite":
            connection = sqlite3.connect(self.path, timeout=15)
            connection.row_factory = sqlite3.Row
            connection.execute("PRAGMA foreign_keys=ON")
            try:
                yield _ConnectionAdapter(connection, postgres=False)
                connection.commit()
            finally:
                connection.close()
            return
        with self._postgres_pool().connection() as connection:
            yield _ConnectionAdapter(connection, postgres=True)
            connection.commit()

    def close(self) -> None:
        if self._pool is not None:
            self._pool.close()
            self._pool = None

    def initialize(self) -> None:
        with self.connect() as connection:
            connection.executescript(SQLITE_SCHEMA if self.backend == "sqlite" else POSTGRES_SCHEMA)
            if self.backend != "sqlite":
                return
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
            row = connection.execute(
                "SELECT * FROM incidents WHERE id = ?", (incident_id,)
            ).fetchone()
        return self._incident(row) if row else None

    def update_incident_status(self, incident_id: str, status: IncidentStatus) -> None:
        with self.connect() as connection:
            connection.execute(
                "UPDATE incidents SET status = ? WHERE id = ?", (status.value, incident_id)
            )

    def add_event(self, event: InvestigationEvent) -> InvestigationEvent:
        with self.connect() as connection:
            sql = """INSERT INTO investigation_events
                (incident_id, event_type, timestamp, stage, summary, metadata_json)
                VALUES (?, ?, ?, ?, ?, ?)"""
            if self.backend == "postgres":
                sql += " RETURNING id"
            cursor = connection.execute(
                sql,
                (
                    event.incident_id,
                    event.event_type.value,
                    event.timestamp.isoformat(),
                    event.stage,
                    event.summary,
                    json.dumps(event.metadata),
                ),
            )
            event.id = cursor.fetchone()["id"] if self.backend == "postgres" else cursor.lastrowid
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
                """INSERT INTO evaluation_summaries
                (id, created_at, summary_json) VALUES (?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                created_at=excluded.created_at, summary_json=excluded.summary_json""",
                (summary.id, summary.created_at.isoformat(), summary.model_dump_json()),
            )

    def list_evaluations(self) -> list[EvaluationSummary]:
        with self.connect() as connection:
            rows = connection.execute(
                "SELECT summary_json FROM evaluation_summaries ORDER BY created_at DESC"
            ).fetchall()
        return [EvaluationSummary.model_validate_json(row["summary_json"]) for row in rows]

    async def ainitialize(self) -> None:
        await asyncio.to_thread(self.initialize)

    async def acreate_incident(self, incident: Incident) -> Incident:
        return await asyncio.to_thread(self.create_incident, incident)

    async def asave_traffic_batch(self, batch: TrafficBatch) -> TrafficBatch:
        return await asyncio.to_thread(self.save_traffic_batch, batch)

    async def aget_traffic_batch(self, batch_id: str) -> TrafficBatch | None:
        return await asyncio.to_thread(self.get_traffic_batch, batch_id)

    async def alatest_traffic_batch(self) -> TrafficBatch | None:
        return await asyncio.to_thread(self.latest_traffic_batch)

    async def alist_incidents(self) -> list[Incident]:
        return await asyncio.to_thread(self.list_incidents)

    async def aget_incident(self, incident_id: str) -> Incident | None:
        return await asyncio.to_thread(self.get_incident, incident_id)

    async def aupdate_incident_status(self, incident_id: str, status: IncidentStatus) -> None:
        await asyncio.to_thread(self.update_incident_status, incident_id, status)

    async def aadd_event(self, event: InvestigationEvent) -> InvestigationEvent:
        return await asyncio.to_thread(self.add_event, event)

    async def alist_events(self, incident_id: str, after_id: int = 0) -> list[InvestigationEvent]:
        return await asyncio.to_thread(self.list_events, incident_id, after_id)

    async def asave_report(self, report: RootCauseReport) -> None:
        await asyncio.to_thread(self.save_report, report)

    async def aget_report(self, incident_id: str) -> RootCauseReport | None:
        return await asyncio.to_thread(self.get_report, incident_id)

    async def asave_evaluation(self, summary: EvaluationSummary) -> None:
        await asyncio.to_thread(self.save_evaluation, summary)

    async def alist_evaluations(self) -> list[EvaluationSummary]:
        return await asyncio.to_thread(self.list_evaluations)

    async def aclose(self) -> None:
        await asyncio.to_thread(self.close)

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


@lru_cache
def get_database() -> Database:
    return Database()
