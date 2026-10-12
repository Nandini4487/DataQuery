from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import chromadb

from app.core.config import settings
from app.services.chunking_service import DocumentChunk
from app.services.document_service import validate_dataset_id, validate_document_id
from app.services.embedding_service import embed_query, embed_texts

logger = logging.getLogger(__name__)

CHROMA_COLLECTION_NAME = "document_chunks"

_chroma_client: chromadb.ClientAPI | None = None


@dataclass
class RetrievalResult:
    """A single retrieved chunk with its text, metadata, and vector distance."""

    text: str
    metadata: dict[str, Any]
    distance: float

    def __getitem__(self, item: str) -> Any:
        if item == "text":
            return self.text
        if item == "metadata":
            return self.metadata
        if item == "distance":
            return self.distance
        raise KeyError(item)

    def to_dict(self) -> dict[str, Any]:
        return {
            "text": self.text,
            "metadata": self.metadata,
            "distance": self.distance,
        }


def get_chroma_client() -> chromadb.ClientAPI:
    """Lazily initialize and return the ChromaDB PersistentClient."""
    global _chroma_client
    if _chroma_client is not None:
        return _chroma_client

    # settings.chroma_persist_directory is already resolved relative to backend/ in config.py
    persist_dir = Path(settings.chroma_persist_directory)
    persist_dir.mkdir(parents=True, exist_ok=True)
    _chroma_client = chromadb.PersistentClient(path=str(persist_dir))
    return _chroma_client


def set_chroma_client(client: chromadb.ClientAPI | None) -> None:
    """Inject a Chroma client (e.g. for testing with an isolated directory)."""
    global _chroma_client
    _chroma_client = client


def reset_chroma_client() -> None:
    """Reset the cached Chroma client to None."""
    global _chroma_client
    _chroma_client = None


def get_chunks_collection(client: chromadb.ClientAPI | None = None) -> Any:
    """Get or create the collection for document chunks without attaching an embedding function."""
    cli = client or get_chroma_client()
    return cli.get_or_create_collection(
        name=CHROMA_COLLECTION_NAME,
        embedding_function=None,
    )


def index_chunks(chunks: list[DocumentChunk]) -> int:
    """Embed and upsert document chunks into the vector store.

    Uses deterministic chunk IDs: <document_id>_<chunk_index>.
    Stores metadata: dataset_id, document_id, filename, page_number, chunk_index.
    """
    if not chunks:
        return 0

    # Validate IDs before indexing
    for c in chunks:
        validate_dataset_id(c.dataset_id)
        validate_document_id(c.document_id)

    texts = [c.text for c in chunks]
    embeddings = embed_texts(texts)

    ids = [f"{c.document_id}_{c.chunk_index}" for c in chunks]
    metadatas: list[dict[str, Any]] = []
    for c in chunks:
        meta: dict[str, Any] = {
            "dataset_id": c.dataset_id,
            "document_id": c.document_id,
            "filename": c.filename,
            "chunk_index": c.chunk_index,
        }
        if c.page_number is not None:
            meta["page_number"] = c.page_number
        metadatas.append(meta)

    collection = get_chunks_collection()
    collection.upsert(
        ids=ids,
        embeddings=embeddings,
        documents=texts,
        metadatas=metadatas,
    )
    return len(chunks)


def retrieve(
    query: str,
    dataset_id: str,
    top_k: int | None = None,
) -> list[RetrievalResult]:
    """Retrieve the most relevant document chunks for a query within a dataset.

    dataset_id is a REQUIRED argument and is ALWAYS passed as a where filter.
    Returns an empty list when nothing matches or the dataset has no chunks.
    """
    if not dataset_id:
        raise ValueError("dataset_id is a required parameter for vector retrieval.")

    clean_ds_id = validate_dataset_id(dataset_id)

    if not isinstance(query, str) or not query.strip():
        return []

    collection = get_chunks_collection()
    total_count = collection.count()
    if total_count == 0:
        return []

    limit = top_k if (top_k is not None and top_k > 0) else settings.rag_top_k
    actual_k = min(limit, total_count)
    if actual_k <= 0:
        return []

    query_emb = embed_query(query)

    query_results = collection.query(
        query_embeddings=[query_emb],
        n_results=actual_k,
        where={"dataset_id": clean_ds_id},
    )

    documents_batch = query_results.get("documents", [[]])
    metadatas_batch = query_results.get("metadatas", [[]])
    distances_batch = query_results.get("distances", [[]])

    docs = documents_batch[0] if documents_batch else []
    metas = metadatas_batch[0] if metadatas_batch else []
    dists = distances_batch[0] if distances_batch else []

    results: list[RetrievalResult] = []
    for doc_text, meta, dist in zip(docs, metas, dists, strict=False):
        cleaned_meta = dict(meta) if meta else {}
        if "page_number" not in cleaned_meta:
            cleaned_meta["page_number"] = None
        results.append(
            RetrievalResult(
                text=doc_text,
                metadata=cleaned_meta,
                distance=float(dist),
            )
        )
    return results


def delete_document(dataset_id: str, document_id: str) -> None:
    """Remove vectors for a document, strictly filtered by BOTH dataset_id and document_id."""
    clean_ds_id = validate_dataset_id(dataset_id)
    clean_doc_id = validate_document_id(document_id)

    collection = get_chunks_collection()
    if collection.count() == 0:
        return

    collection.delete(
        where={
            "$and": [
                {"dataset_id": clean_ds_id},
                {"document_id": clean_doc_id},
            ]
        }
    )


def delete_dataset(dataset_id: str) -> None:
    """Remove all vectors for a dataset."""
    clean_ds_id = validate_dataset_id(dataset_id)

    collection = get_chunks_collection()
    if collection.count() == 0:
        return

    collection.delete(where={"dataset_id": clean_ds_id})
