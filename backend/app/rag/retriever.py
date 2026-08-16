from __future__ import annotations

from langsmith import traceable

from app.core.config import Settings, get_settings
from app.domain.models import RetrievedDocument
from app.rag.ingest import ensure_vector_store
from app.rag.schemas import RetrieverStrategy


def build_retriever(
    strategy: RetrieverStrategy = RetrieverStrategy.MMR, settings: Settings | None = None
):
    settings = settings or get_settings()
    store = ensure_vector_store(settings)
    return store.as_retriever(
        search_type=strategy.value,
        search_kwargs={"k": 5, "fetch_k": 10, "lambda_mult": 0.75},
    )


@traceable(run_type="retriever", name="retrieve_operational_knowledge")
async def retrieve_documents(
    query: str,
    strategy: RetrieverStrategy = RetrieverStrategy.MMR,
    settings: Settings | None = None,
) -> list[RetrievedDocument]:
    documents = await build_retriever(strategy, settings).ainvoke(query)
    return [
        RetrievedDocument(
            evidence_id=document.metadata["evidence_id"],
            content=document.page_content,
            source=document.metadata["source"],
            document_type=document.metadata.get("document_type", "document"),
            service=document.metadata.get("service"),
            failure_type=document.metadata.get("failure_type"),
        )
        for document in documents
    ]
