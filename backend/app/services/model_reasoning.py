from __future__ import annotations

import json
from typing import TypeVar

from langchain_openai import ChatOpenAI
from pydantic import BaseModel

from app.core.config import Settings, get_settings

SchemaT = TypeVar("SchemaT", bound=BaseModel)


class StructuredReasoner:
    def __init__(self, settings: Settings | None = None):
        self.settings = settings or get_settings()
        self.enabled = bool(self.settings.openai_api_key)
        self.model = (
            ChatOpenAI(
                model=self.settings.openai_chat_model,
                api_key=self.settings.openai_api_key,
                temperature=0,
            )
            if self.enabled
            else None
        )

    async def invoke(
        self, schema: type[SchemaT], instruction: str, context: dict
    ) -> SchemaT:
        if not self.model:
            raise RuntimeError("OPENAI_API_KEY is not configured")
        structured = self.model.with_structured_output(schema, method="json_schema")
        result = await structured.ainvoke(
            [
                ("system", instruction),
                ("human", json.dumps(context, default=str, separators=(",", ":"))),
            ]
        )
        if not isinstance(result, schema):
            return schema.model_validate(result)
        return result

