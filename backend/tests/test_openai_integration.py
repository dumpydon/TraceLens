import os

import pytest

from app.domain.models import RuntimeAnalysis
from app.services.model_reasoning import StructuredReasoner


@pytest.mark.integration
@pytest.mark.skipif(not os.getenv("OPENAI_API_KEY"), reason="OPENAI_API_KEY is not configured")
async def test_openai_structured_output_integration():
    result = await StructuredReasoner().invoke(
        RuntimeAnalysis,
        "Return a typed runtime analysis. Cite only log:payment:1.",
        {
            "evidence": [
                {
                    "id": "log:payment:1",
                    "service": "payment-service",
                    "duration_ms": 1800,
                    "status_code": 200,
                }
            ]
        },
    )
    assert isinstance(result, RuntimeAnalysis)
