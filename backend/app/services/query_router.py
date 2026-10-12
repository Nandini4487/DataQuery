from __future__ import annotations


# TODO: document/combined/unsupported routing comes in Phase 3.
def classify_question(question: str, dataset_id: str | None = None) -> str:
    """Classify the incoming question into an analysis category.

    In Phase 2, this stub unconditionally routes every query to 'structured'.
    Phase 3 will add classification for document, combined, and unsupported questions.
    """
    return "structured"
