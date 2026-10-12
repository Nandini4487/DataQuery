from __future__ import annotations

import uuid

import pytest

from app.services.chunking_service import DocumentChunk
from app.services.document_service import DocumentValidationError
from app.services.retrieval_service import (
    delete_dataset,
    delete_document,
    get_chunks_collection,
    index_chunks,
    retrieve,
)


def _make_chunk(
    dataset_id: str,
    document_id: str,
    text: str,
    chunk_index: int = 0,
    page_number: int | None = 1,
    filename: str = "doc.pdf",
) -> DocumentChunk:
    return DocumentChunk(
        text=text,
        dataset_id=dataset_id,
        document_id=document_id,
        filename=filename,
        page_number=page_number,
        chunk_index=chunk_index,
    )


def test_index_under_dataset_a_retrieve_with_dataset_b_returns_nothing(
    temp_chroma_client: object,
) -> None:
    """Chunks indexed under dataset A must never appear in queries for dataset B."""
    ds_a = str(uuid.uuid4())
    ds_b = str(uuid.uuid4())
    doc_a = str(uuid.uuid4())

    chunk = _make_chunk(ds_a, doc_a, "Confidential financial roadmap for dataset A.")
    index_chunks([chunk])

    # Query for dataset B
    results_b = retrieve("financial roadmap", dataset_id=ds_b)
    assert results_b == []

    # Query for dataset A
    results_a = retrieve("financial roadmap", dataset_id=ds_a)
    assert len(results_a) == 1
    assert results_a[0].text == chunk.text
    assert results_a[0].metadata["dataset_id"] == ds_a


def test_identical_text_in_two_datasets_stays_separate(
    temp_chroma_client: object,
) -> None:
    """Identical text passages stored in two datasets must remain strictly isolated."""
    ds_a = str(uuid.uuid4())
    ds_b = str(uuid.uuid4())
    doc_a = str(uuid.uuid4())
    doc_b = str(uuid.uuid4())

    same_text = "Gross margin was 42 percent across all product categories."
    chunk_a = _make_chunk(ds_a, doc_a, same_text, filename="a.txt")
    chunk_b = _make_chunk(ds_b, doc_b, same_text, filename="b.txt")

    index_chunks([chunk_a, chunk_b])

    res_a = retrieve("gross margin", dataset_id=ds_a)
    assert len(res_a) == 1
    assert res_a[0].metadata["dataset_id"] == ds_a
    assert res_a[0].metadata["document_id"] == doc_a

    res_b = retrieve("gross margin", dataset_id=ds_b)
    assert len(res_b) == 1
    assert res_b[0].metadata["dataset_id"] == ds_b
    assert res_b[0].metadata["document_id"] == doc_b


def test_retrieve_returns_expected_chunk_for_close_query(
    temp_chroma_client: object,
) -> None:
    """Retrieve must rank the closest matching chunk first."""
    ds_id = str(uuid.uuid4())
    doc_id = str(uuid.uuid4())

    target_text = "Quantum computing algorithms using superconducting qubits."
    distractor_text = "Traditional Italian pasta recipes with basil and parmesan."

    c1 = _make_chunk(ds_id, doc_id, target_text, chunk_index=0)
    c2 = _make_chunk(ds_id, doc_id, distractor_text, chunk_index=1)
    index_chunks([c1, c2])

    results = retrieve(target_text, dataset_id=ds_id, top_k=2)
    assert len(results) == 2
    # The exact matching query produces distance 0.0 with the deterministic fake embedding
    assert results[0].text == target_text
    assert results[0].distance == pytest.approx(0.0, abs=1e-4)


def test_delete_document_removes_only_that_document(
    temp_chroma_client: object,
) -> None:
    """Deleting a document must delete its chunks without affecting other documents in the dataset."""
    ds_id = str(uuid.uuid4())
    doc_1 = str(uuid.uuid4())
    doc_2 = str(uuid.uuid4())

    c1 = _make_chunk(ds_id, doc_1, "Document one content.", chunk_index=0)
    c2 = _make_chunk(ds_id, doc_2, "Document two content.", chunk_index=0)
    index_chunks([c1, c2])

    delete_document(dataset_id=ds_id, document_id=doc_1)

    results = retrieve("content", dataset_id=ds_id, top_k=5)
    assert len(results) == 1
    assert results[0].metadata["document_id"] == doc_2


def test_delete_dataset_removes_all_vectors_for_dataset(
    temp_chroma_client: object,
) -> None:
    """Deleting a dataset must remove all its chunks and preserve chunks in other datasets."""
    ds_a = str(uuid.uuid4())
    ds_b = str(uuid.uuid4())
    doc_a = str(uuid.uuid4())
    doc_b = str(uuid.uuid4())

    c_a = _make_chunk(ds_a, doc_a, "Dataset A data.")
    c_b = _make_chunk(ds_b, doc_b, "Dataset B data.")
    index_chunks([c_a, c_b])

    delete_dataset(dataset_id=ds_a)

    assert retrieve("data", dataset_id=ds_a) == []
    res_b = retrieve("data", dataset_id=ds_b)
    assert len(res_b) == 1
    assert res_b[0].metadata["dataset_id"] == ds_b


def test_retrieve_cannot_be_called_without_dataset_id() -> None:
    """Calling retrieve without a valid dataset_id must raise an error."""
    with pytest.raises(ValueError, match="dataset_id is a required parameter"):
        retrieve("query", dataset_id="")

    with pytest.raises(DocumentValidationError):
        retrieve("query", dataset_id="invalid-not-uuid")


def test_reindexing_same_chunks_does_not_create_duplicates(
    temp_chroma_client: object,
) -> None:
    """Re-indexing identical chunks (same document_id and chunk_index) must not duplicate entries."""
    ds_id = str(uuid.uuid4())
    doc_id = str(uuid.uuid4())

    chunk = _make_chunk(ds_id, doc_id, "Sample idempotency content.", chunk_index=0)

    index_chunks([chunk])
    col = get_chunks_collection()
    initial_count = col.count()
    assert initial_count == 1

    # Re-index the same chunk
    index_chunks([chunk])
    assert col.count() == initial_count
