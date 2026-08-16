from __future__ import annotations

from contextlib import asynccontextmanager

import aiosqlite
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

from app.core.config import Settings, get_settings
from app.core.database import Database, get_database
from app.domain.models import IncidentStatus, InvestigationEvent, InvestigationEventType
from app.graph.nodes import InvestigationNodes
from app.graph.state import initial_state
from app.graph.workflow import build_workflow


def checkpoint_serializer() -> JsonPlusSerializer:
    """Allow only the TraceLens domain records persisted in graph state."""
    from app.domain import models

    allowed_types = [
        models.Severity,
        models.IncidentStatus,
        models.FailureType,
        models.ConfidenceLevel,
        models.Incident,
        models.LogEntry,
        models.Deployment,
        models.ServiceHealth,
        models.RetrievedDocument,
        models.EvidenceKind,
        models.EvidenceItem,
        models.RuntimeAnalysis,
        models.Hypothesis,
        models.VerificationResult,
        models.EvidenceConfidence,
        models.ReportEvidence,
        models.RootCauseReportDraft,
        models.RootCauseReport,
    ]
    return JsonPlusSerializer(allowed_msgpack_modules=allowed_types)


def checkpoint_backend(settings: Settings) -> str:
    return "postgres" if settings.database_backend == "postgres" else "sqlite"


@asynccontextmanager
async def investigation_checkpointer(settings: Settings):
    serializer = checkpoint_serializer()
    if checkpoint_backend(settings) == "postgres":
        database_url = settings.database_url.replace("postgres://", "postgresql://", 1)
        async with AsyncPostgresSaver.from_conn_string(
            database_url, serde=serializer
        ) as checkpointer:
            await checkpointer.setup()
            yield checkpointer
        return
    async with aiosqlite.connect(str(settings.checkpoint_database_path)) as connection:
        yield AsyncSqliteSaver(connection, serde=serializer)


def graph_config(incident_id: str, settings: Settings) -> dict:
    return {
        "configurable": {"thread_id": incident_id},
        "tags": [
            "tracelens",
            settings.environment,
            settings.retriever_strategy,
            settings.graph_version,
        ],
        "metadata": {
            "incident_id": incident_id,
            "thread_id": incident_id,
            "retriever_strategy": settings.retriever_strategy,
            "graph_version": settings.graph_version,
            "environment": settings.environment,
        },
        "recursion_limit": 40,
    }


async def run_investigation(
    incident_id: str,
    *,
    resume: bool = False,
    database: Database | None = None,
    settings: Settings | None = None,
) -> None:
    settings = settings or get_settings()
    database = database or get_database()
    config = graph_config(incident_id, settings)
    if not resume:
        await database.aadd_event(
            InvestigationEvent(
                event_type=InvestigationEventType.INVESTIGATION_STARTED,
                incident_id=incident_id,
                stage="start",
                summary="Investigation started",
            )
        )
    try:
        async with investigation_checkpointer(settings) as checkpointer:
            graph = build_workflow(InvestigationNodes(database, settings), checkpointer)
            graph_input = (
                None
                if resume
                else initial_state(incident_id, settings.max_investigation_iterations)
            )
            async for _ in graph.astream(graph_input, config=config, stream_mode="updates"):
                pass
    except Exception as exc:
        await database.aupdate_incident_status(incident_id, IncidentStatus.FAILED)
        await database.aadd_event(
            InvestigationEvent(
                event_type=InvestigationEventType.INVESTIGATION_FAILED,
                incident_id=incident_id,
                stage="error",
                summary=f"Investigation failed: {type(exc).__name__}",
                metadata={"error": str(exc)[:500]},
            )
        )
        raise


async def load_checkpoint_state(
    incident_id: str,
    settings: Settings | None = None,
) -> dict:
    settings = settings or get_settings()
    async with investigation_checkpointer(settings) as checkpointer:
        graph = build_workflow(checkpointer=checkpointer)
        snapshot = await graph.aget_state(graph_config(incident_id, settings))
        return dict(snapshot.values) if snapshot.values else {}
