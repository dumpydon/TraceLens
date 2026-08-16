from app.rag.ingest import load_documents, split_documents


def test_rag_ingestion_preserves_source_metadata(settings):
    chunks = split_documents(load_documents(settings.knowledge_directory))
    latency = next(item for item in chunks if item.metadata.get("failure_type") == "payment_latency")
    assert latency.metadata["source"].startswith(("runbooks/", "postmortems/"))
    assert latency.metadata["evidence_id"].endswith("chunk-01")
    assert latency.metadata["service"] == "payment-service"

