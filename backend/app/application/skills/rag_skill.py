"""Plain callable — no SDK import (per ARCHITECTURE.md §4.7).

Retrieves grounded context for a product/growth question via
RetrieveContextUseCase and shapes it into the tool-result payload the model
uses to compose a cited answer (or decline, per the §11.5 RAG prompt
contract, if nothing relevant was found).
"""

from app.application.use_cases.retrieve_context import RetrieveContextUseCase
from app.domain.entities.search_result import SearchResult

# PRD §11.5's RAG prompt contract, returned with the retrieved chunks. The
# harness system prompt already forbids answering from general knowledge; this
# adds the per-answer rules (exact decline wording, citation requirement) at
# the point where the context actually arrives.
RAG_GUIDANCE = (
    "Answer ONLY using the retrieved context above. Never invent information. "
    "Cite the episode (and speaker/timestamp when available)."
)
RAG_NOT_FOUND_GUIDANCE = (
    "Nothing relevant was retrieved. Reply exactly: "
    "\"I couldn't find this in Lenny's transcripts.\" "
    "Do not answer from general knowledge."
)


def _citation(result: SearchResult) -> str:
    document = result.document
    citation = f"{document.episode}"
    # Corpus episode titles already end with the guest's name ("Pricing your AI
    # product ... | Madhavan Ramanujam"), so appending the speaker
    # unconditionally rendered "... | Madhavan Ramanujam — Madhavan Ramanujam"
    # on the citation cards. Only add it when it isn't already in the title.
    if document.speaker and document.speaker not in document.episode:
        citation += f" — {document.speaker}"
    if document.timestamp_range:
        citation += f" [{document.timestamp_range}]"
    return citation


def rag_query(question: str, retrieve_context: RetrieveContextUseCase) -> dict:
    context = retrieve_context.execute(question)

    if not context.found:
        return {"found": False, "chunks": [], "citations": [], "guidance": RAG_NOT_FOUND_GUIDANCE}

    chunks = [
        {"text": result.document.chunk, "citation": _citation(result), "score": result.score}
        for result in context.results
    ]
    citations = [chunk["citation"] for chunk in chunks]

    return {"found": True, "chunks": chunks, "citations": citations, "guidance": RAG_GUIDANCE}
