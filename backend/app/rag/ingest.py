from __future__ import annotations

import hashlib
import re
from collections.abc import Iterable
from pathlib import Path

from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_openai import OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.core.config import Settings, get_settings

COLLECTION_NAME = "tracelens-operations-v1"


class LocalHashEmbeddings(Embeddings):
    """Credential-free local fallback for tests and UI exploration, not the production retriever."""

    dimensions = 1024

    def _embed(self, text: str) -> list[float]:
        vector = [0.0] * self.dimensions
        for token in re.findall(r"[a-z0-9_]+", text.lower()):
            digest = hashlib.sha256(token.encode()).digest()
            index = int.from_bytes(digest[:2], "big") % self.dimensions
            vector[index] += 1.0
        magnitude = sum(value * value for value in vector) ** 0.5 or 1.0
        return [value / magnitude for value in vector]

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._embed(text) for text in texts]

    def embed_query(self, text: str) -> list[float]:
        return self._embed(text)


def build_embeddings(settings: Settings | None = None) -> Embeddings:
    settings = settings or get_settings()
    if settings.openai_api_key:
        return OpenAIEmbeddings(model=settings.openai_embedding_model, api_key=settings.openai_api_key)
    return LocalHashEmbeddings()


def parse_markdown(path: Path, knowledge_root: Path) -> Document:
    text = path.read_text(encoding="utf-8")
    metadata: dict[str, str] = {"source": str(path.relative_to(knowledge_root))}
    if text.startswith("---\n"):
        _, header, text = text.split("---\n", 2)
        for line in header.splitlines():
            if ":" in line:
                key, value = line.split(":", 1)
                metadata[key.strip()] = value.strip()
    return Document(page_content=text.strip(), metadata=metadata)


def load_documents(knowledge_root: Path) -> list[Document]:
    return [parse_markdown(path, knowledge_root) for path in sorted(knowledge_root.rglob("*.md"))]


def split_documents(documents: Iterable[Document]) -> list[Document]:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=800,
        chunk_overlap=120,
        separators=["\n## ", "\n# ", "\n\n", "\n", " "],
    )
    chunks = splitter.split_documents(list(documents))
    source_counts: dict[str, int] = {}
    for chunk in chunks:
        source = chunk.metadata["source"]
        index = source_counts.get(source, 0)
        source_counts[source] = index + 1
        slug = Path(source).stem
        chunk.metadata["evidence_id"] = f"{chunk.metadata.get('document_type', 'document')}:{slug}:chunk-{index + 1:02d}"
        chunk.metadata["chunk_index"] = index
    return chunks


def build_vector_store(settings: Settings | None = None) -> Chroma:
    settings = settings or get_settings()
    embedding_label = (
        settings.openai_embedding_model.replace("_", "-").replace(".", "-")
        if settings.openai_api_key
        else "local-hash-v2"
    )
    return Chroma(
        collection_name=f"{COLLECTION_NAME}-{embedding_label}",
        embedding_function=build_embeddings(settings),
        persist_directory=str(settings.chroma_persist_directory),
    )


def ingest_knowledge(settings: Settings | None = None) -> int:
    settings = settings or get_settings()
    documents = split_documents(load_documents(settings.knowledge_directory))
    store = build_vector_store(settings)
    store.add_documents(documents, ids=[doc.metadata["evidence_id"] for doc in documents])
    return len(documents)


def main() -> None:
    count = ingest_knowledge()
    print(f"Ingested {count} operational knowledge chunks into {COLLECTION_NAME}.")


if __name__ == "__main__":
    main()
