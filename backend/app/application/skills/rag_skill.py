"""Plain callable — no SDK import (per ARCHITECTURE.md §4.7).

Placeholder until Phase 4 (infrastructure/vectorstore + infrastructure/ingestion)
exists. Not wired to any fake or in-memory retrieval — this file exists so the
skill's interface contract is in place before the real implementation lands.
"""


def rag_query(question: str) -> dict:
    raise NotImplementedError(
        "rag_query is a placeholder. Implement grounded retrieval once "
        "infrastructure/vectorstore (Phase 4) exists."
    )
