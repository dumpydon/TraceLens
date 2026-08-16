from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from incident_lab.runtime.store import ensure_runtime

from app.api.routes import router
from app.core.config import get_settings
from app.core.database import Database
from app.observability.langsmith import configure_langsmith


@asynccontextmanager
async def lifespan(_: FastAPI):
    settings = get_settings()
    settings.ensure_directories()
    configure_langsmith(settings)
    Database().initialize()
    ensure_runtime()
    yield


app = FastAPI(
    title="TraceLens API",
    version="0.1.0",
    description="Evidence-first incident investigation for the executable Incident Lab.",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:3000", "http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "healthy", "service": "tracelens-api"}

