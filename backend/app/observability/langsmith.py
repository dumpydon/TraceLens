import os

from app.core.config import Settings, get_settings


def configure_langsmith(settings: Settings | None = None) -> bool:
    settings = settings or get_settings()
    enabled = bool(settings.langsmith_tracing and settings.langsmith_api_key)
    os.environ["LANGSMITH_TRACING"] = "true" if enabled else "false"
    os.environ["LANGSMITH_PROJECT"] = settings.langsmith_project
    if enabled and settings.langsmith_api_key:
        os.environ["LANGSMITH_API_KEY"] = settings.langsmith_api_key
    return enabled

