from pathlib import Path

import pytest

from app.core.config import Settings
from app.core.database import Database


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    return Settings(
        database_url=f"sqlite:///{tmp_path / 'test.db'}",
        checkpoint_database_path=tmp_path / "checkpoints.db",
        runtime_directory=tmp_path / "runtime",
        chroma_persist_directory=tmp_path / "chroma",
        knowledge_directory=Path(__file__).resolve().parents[2] / "knowledge",
        openai_api_key=None,
    )


@pytest.fixture
def database(settings: Settings) -> Database:
    db = Database(settings.database_path)
    db.initialize()
    return db

