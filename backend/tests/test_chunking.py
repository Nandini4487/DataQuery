from __future__ import annotations

import uuid

import pytest
from pydantic import ValidationError

from app.core.config import Settings
from app.services.chunking_service import (
    ChunkingError,
    chunk_document_pages,
)


def _generate_words(n: int, prefix: str = "word") -> str:
    return " ".join(f"{prefix}_{i}" for i in range(n))


def test_chunk_count_for_known_word_count() -> None:
    """900 words with chunk_size 450 and overlap 80 should produce 3 chunks."""
    ds_id = str(uuid.uuid4())
    doc_id = str(uuid.uuid4())
    text = _generate_words(900)
    pages = [{"page_number": 1, "text": text}]

    chunks = chunk_document_pages(
        pages,
        dataset_id=ds_id,
        document_id=doc_id,
        filename="report.pdf",
        chunk_size_words=450,
        chunk_overlap_words=80,
    )

    # start 0..450 (step 370), start 370..820 (step 370), start 740..900 -> 3 chunks
    assert len(chunks) == 3


def test_overlap_between_neighboring_chunks() -> None:
    """Verify that neighboring chunks share exactly chunk_overlap_words."""
    ds_id = str(uuid.uuid4())
    doc_id = str(uuid.uuid4())
    text = _generate_words(600)
    pages = [{"page_number": 1, "text": text}]

    overlap = 80
    size = 200
    chunks = chunk_document_pages(
        pages,
        dataset_id=ds_id,
        document_id=doc_id,
        filename="doc.txt",
        chunk_size_words=size,
        chunk_overlap_words=overlap,
    )

    assert len(chunks) >= 2
    for i in range(len(chunks) - 1):
        words_curr = chunks[i].text.split()
        words_next = chunks[i + 1].text.split()
        assert words_curr[-overlap:] == words_next[:overlap]


def test_every_chunk_has_all_metadata_fields() -> None:
    """Ensure all required metadata attributes exist and match on every chunk."""
    ds_id = str(uuid.uuid4())
    doc_id = str(uuid.uuid4())
    pages = [
        {"page_number": 1, "text": "Page one text content here."},
        {"page_number": 2, "text": "Page two text content here."},
    ]

    chunks = chunk_document_pages(
        pages,
        dataset_id=ds_id,
        document_id=doc_id,
        filename="annual.pdf",
    )

    assert len(chunks) == 2
    for chunk in chunks:
        assert chunk.dataset_id == ds_id
        assert chunk.document_id == doc_id
        assert chunk.filename == "annual.pdf"
        assert chunk.page_number in (1, 2)
        assert isinstance(chunk.chunk_index, int)
        assert isinstance(chunk.text, str)
        assert len(chunk.text) > 0


def test_no_chunk_crosses_page_boundary() -> None:
    """A chunk must never combine text across two different pages."""
    ds_id = str(uuid.uuid4())
    doc_id = str(uuid.uuid4())
    # Two pages, each smaller than the chunk size (450)
    pages = [
        {"page_number": 1, "text": _generate_words(100, prefix="p1")},
        {"page_number": 2, "text": _generate_words(100, prefix="p2")},
    ]

    chunks = chunk_document_pages(
        pages,
        dataset_id=ds_id,
        document_id=doc_id,
        filename="multipage.pdf",
        chunk_size_words=450,
        chunk_overlap_words=80,
    )

    assert len(chunks) == 2
    assert chunks[0].page_number == 1
    assert all(w.startswith("p1_") for w in chunks[0].text.split())
    assert chunks[1].page_number == 2
    assert all(w.startswith("p2_") for w in chunks[1].text.split())


def test_chunk_index_runs_continuously_across_pages() -> None:
    """chunk_index must increment 0, 1, 2, ... monotonically across the entire document."""
    ds_id = str(uuid.uuid4())
    doc_id = str(uuid.uuid4())
    # Each page generates 2 chunks with size 100, overlap 20 (step 80)
    pages = [
        {"page_number": 1, "text": _generate_words(150, prefix="p1")},
        {"page_number": 2, "text": _generate_words(150, prefix="p2")},
    ]

    chunks = chunk_document_pages(
        pages,
        dataset_id=ds_id,
        document_id=doc_id,
        filename="numbered.pdf",
        chunk_size_words=100,
        chunk_overlap_words=20,
    )

    assert len(chunks) == 4
    for idx, chunk in enumerate(chunks):
        assert chunk.chunk_index == idx


def test_chunk_limit_is_enforced() -> None:
    """If a document would produce more chunks than max_chunks_per_document, raise safe error."""
    ds_id = str(uuid.uuid4())
    doc_id = str(uuid.uuid4())
    pages = [{"page_number": 1, "text": _generate_words(600)}]

    with pytest.raises(ChunkingError) as exc_info:
        chunk_document_pages(
            pages,
            dataset_id=ds_id,
            document_id=doc_id,
            filename="big.pdf",
            chunk_size_words=100,
            chunk_overlap_words=20,
            max_chunks=3,
        )

    err = exc_info.value
    assert err.error_code == "too_many_chunks"
    assert "limit of 3 chunks" in err.message
    assert err.to_dict() == {"error": "too_many_chunks", "message": err.message}


def test_whitespace_only_text_produces_no_chunks() -> None:
    """Empty or whitespace-only pages must be skipped and produce 0 chunks."""
    ds_id = str(uuid.uuid4())
    doc_id = str(uuid.uuid4())
    pages = [
        {"page_number": 1, "text": "   \n\t  "},
        {"page_number": 2, "text": ""},
        {"page_number": 3, "text": "   "},
    ]

    chunks = chunk_document_pages(
        pages,
        dataset_id=ds_id,
        document_id=doc_id,
        filename="empty.pdf",
    )
    assert chunks == []


def test_bad_overlap_config_rejected() -> None:
    """Overlap >= chunk size must be rejected in chunking and Settings."""
    ds_id = str(uuid.uuid4())
    doc_id = str(uuid.uuid4())
    pages = [{"page_number": 1, "text": "Some text"}]

    with pytest.raises(ChunkingError, match="strictly less than"):
        chunk_document_pages(
            pages,
            dataset_id=ds_id,
            document_id=doc_id,
            filename="doc.txt",
            chunk_size_words=100,
            chunk_overlap_words=100,
        )

    with pytest.raises(ValidationError, match="strictly less than"):
        Settings(chunk_size_words=100, chunk_overlap_words=150)
