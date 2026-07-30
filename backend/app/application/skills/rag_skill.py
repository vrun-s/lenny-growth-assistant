"""Plain callable — no SDK import (per ARCHITECTURE.md §4.7).

Retrieves grounded context for a product/growth question via
RetrieveContextUseCase and shapes it into the tool-result payload the model
uses to compose a cited answer (or decline, per the §11.5 RAG prompt
contract, if nothing relevant was found).
"""

from app.application.use_cases.retrieve_context import RetrieveContextUseCase
from app.domain.entities.search_result import SearchResult


def _citation(result: SearchResult) -> str:
    document = result.document
    citation = f"{document.episode}"
    if document.speaker:
        citation += f" — {document.speaker}"
    if document.timestamp_range:
        citation += f" [{document.timestamp_range}]"
    return citation


def rag_query(question: str, retrieve_context: RetrieveContextUseCase) -> dict:
    context = retrieve_context.execute(question)

    if not context.found:
        return {"found": False, "chunks": [], "citations": []}

    chunks = [
        {"text": result.document.chunk, "citation": _citation(result), "score": result.score}
        for result in context.results
    ]
    citations = [chunk["citation"] for chunk in chunks]

    return {"found": True, "chunks": chunks, "citations": citations}
