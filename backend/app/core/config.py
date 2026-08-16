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
    checkout_service_url: str = "http://127.0.0.1:8101"
    payment_service_url: str = "http://127.0.0.1:8102"
    graph_version: str = "v1"
    retriever_strategy: str = "mmr"
    max_investigation_iterations: int = Field(default=3, ge=1, le=5)

    @property
    def database_path(self) -> Path:
        prefix = "sqlite:///"
        if not self.database_url.startswith(prefix):
            raise ValueError("V1 supports sqlite:/// DATABASE_URL values only")
        return Path(self.database_url.removeprefix(prefix)).expanduser().resolve()

    def ensure_directories(self) -> None:
        for path in (
            self.database_path.parent,
            self.checkpoint_database_path.parent,
            self.runtime_directory,
            self.chroma_persist_directory,
        ):
            path.mkdir(parents=True, exist_ok=True)


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.ensure_directories()
    return settings

