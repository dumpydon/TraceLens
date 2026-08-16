import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from incident_lab.checkout_service.main import app as checkout_app
from incident_lab.payment_service.main import app as payment_app
from incident_lab.runtime.store import (
    close_runtime_storage,
    configure_runtime,
    ensure_runtime,
)

from app.api.routes import router
from app.core.config import Settings, get_settings
from app.core.database import get_database
from app.observability.langsmith import configure_langsmith
from app.rag.ingest import ensure_vector_store


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings: Settings = app.state.settings
    settings.ensure_directories()
    configure_langsmith(settings)
    configure_runtime(settings.runtime_directory, settings.database_url)
    database = get_database()
    await database.ainitialize()
    await asyncio.to_thread(ensure_runtime)
    if settings.embedded_incident_lab:
        await asyncio.to_thread(ensure_vector_store, settings)
    yield
    await database.aclose()
    await asyncio.to_thread(close_runtime_storage)


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    application = FastAPI(
        title="TraceLens API",
        version="0.1.0",
        description="Evidence-first incident investigation for the executable Incident Lab.",
        lifespan=lifespan,
    )
    application.state.settings = settings
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    application.include_router(router)
    application.mount("/_internal/lab/checkout", checkout_app)
    application.mount("/_internal/lab/payment", payment_app)

    @application.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "healthy", "service": "tracelens-api"}

    return application


app = create_app()
