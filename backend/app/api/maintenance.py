import logging
import secrets
import sqlite3
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from psycopg import Error as PostgresError
from psycopg_pool import PoolTimeout

from app.core.database import Database, get_database

router = APIRouter(prefix="/internal/maintenance", include_in_schema=False)
bearer = HTTPBearer(auto_error=False)
logger = logging.getLogger(__name__)


@router.post("/heartbeat")
def heartbeat(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
    database: Annotated[Database, Depends(get_database)],
) -> dict[str, str]:
    configured = request.app.state.settings.tracelens_keepalive_secret
    if configured is None or not configured.get_secret_value():
        raise HTTPException(status_code=503, detail="Maintenance unavailable")
    if credentials is None or not secrets.compare_digest(
        credentials.credentials.encode(), configured.get_secret_value().encode()
    ):
        raise HTTPException(status_code=401, detail="Unauthorized")

    try:
        database.heartbeat()
    except (PostgresError, PoolTimeout, sqlite3.Error, OSError, RuntimeError):
        # Driver exceptions can contain connection strings; never log their contents.
        logger.warning("maintenance.database_heartbeat_failed")
        raise HTTPException(status_code=503, detail="Database unavailable") from None

    return {
        "status": "ok",
        "database": "postgresql" if database.backend == "postgres" else "sqlite",
        "checked_at": datetime.now(UTC).isoformat(),
    }
