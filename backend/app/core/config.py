from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(ROOT / ".env",), env_file_encoding="utf-8", extra="ignore"
    )

    app_name: str = "TraceLens"
    environment: str = "development"
    database_url: str = f"sqlite:///{ROOT / 'data' / 'tracelens.db'}"
    checkpoint_database_path: Path = ROOT / "data" / "checkpoints.db"
    runtime_directory: Path = ROOT / "data" / "runtime"
    chroma_persist_directory: Path = ROOT / "data" / "chroma"
    knowledge_directory: Path = ROOT / "knowledge"
    openai_api_key: str | None = None
    openai_chat_model: str = "gpt-4.1-mini"
    openai_embedding_model: str = "text-embedding-3-small"
    langsmith_tracing: bool = False
    langsmith_api_key: str | None = None
    langsmith_project: str = "tracelens-dev"
    frontend_origin: str | None = None
    checkout_service_url: str = "http://127.0.0.1:8101"
    payment_service_url: str = "http://127.0.0.1:8102"
    graph_version: str = "v1"
    retriever_strategy: str = "mmr"
    max_investigation_iterations: int = Field(default=3, ge=1, le=5)

    @property
    def database_path(self) -> Path:
        prefix = "sqlite:///"
        if not self.database_url.startswith(prefix):
            raise ValueError("database_path is available only for SQLite DATABASE_URL values")
        return Path(self.database_url.removeprefix(prefix)).expanduser().resolve()

    @property
    def database_backend(self) -> str:
        if self.database_url.startswith("sqlite:///"):
            return "sqlite"
        if self.database_url.startswith(("postgresql://", "postgres://")):
            return "postgres"
        raise ValueError("DATABASE_URL must use sqlite:/// or postgresql://")

    @property
    def embedded_incident_lab(self) -> bool:
        return self.environment.lower() == "production"

    @property
    def cors_origins(self) -> list[str]:
        origins = ["http://127.0.0.1:3000", "http://localhost:3000"]
        if self.frontend_origin:
            origin = self.frontend_origin.rstrip("/")
            if origin not in origins:
                origins.append(origin)
        return origins

    def ensure_directories(self) -> None:
        paths = [
            self.checkpoint_database_path.parent,
            self.runtime_directory,
            self.chroma_persist_directory,
        ]
        if self.database_backend == "sqlite":
            paths.append(self.database_path.parent)
        for path in paths:
            path.mkdir(parents=True, exist_ok=True)


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.ensure_directories()
    return settings
