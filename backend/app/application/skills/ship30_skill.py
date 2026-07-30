"""Plain callable — no SDK import (per ARCHITECTURE.md §4.7).

Pulls a broader spread of grounded material across episodes for a topic via
RetrieveContextUseCase. The essay itself is the model's own generation in its
next turn, constrained by the §11.5 Ship30 structure — this skill only
assembles the material and citations it's grounded in.
"""

from app.application.use_cases.retrieve_context import RetrieveContextUseCase
from app.domain.entities.search_result import SearchResult

SHIP30_TOP_K = 10


def _citation(result: SearchResult) -> str:
    document = result.document
    citation = f"{document.episode}"
    if document.speaker:
        citation += f" — {document.speaker}"
    if document.timestamp_range:
        citation += f" [{document.timestamp_range}]"
    return citation


def write_ship30_essay(topic: str, retrieve_context: RetrieveContextUseCase) -> dict:
    context = retrieve_context.execute(topic, top_k=SHIP30_TOP_K)

    if not context.found:
        return {"found": False, "topic": topic, "material": [], "citations": []}

    material = [
        {"text": result.document.chunk, "citation": _citation(result), "episode": result.document.episode}
        for result in context.results
    ]
    citations = [item["citation"] for item in material]

    return {"found": True, "topic": topic, "material": material, "citations": citations}
