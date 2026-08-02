"""Plain callable — no SDK import (per ARCHITECTURE.md §4.7).

Pulls a broader spread of grounded material across episodes for a topic via
RetrieveContextUseCase. The essay itself is the model's own generation in its
next turn, constrained by the §11.5 Ship30 structure — this skill only
assembles the material and citations it's grounded in.
"""

from app.application.use_cases.retrieve_context import RetrieveContextUseCase
from app.domain.entities.search_result import SearchResult

SHIP30_TOP_K = 10

# PRD §11.5's Ship30 prompt contract, returned to the model alongside the
# retrieved material. It lives in the tool *result* rather than the harness
# system prompt because it only applies to this one tool — a RAG answer or an
# artifact must not inherit essay structure. Previously the whole contract was
# carried implicitly by the tool's name and description, so structure and
# length were left entirely to the model's own priors about "Ship30for30".
SHIP30_GUIDANCE = (
    "Write a ~1250-word essay in the Ship30for30 style, using ONLY the "
    "retrieved material provided here.\n\n"
    "Structure:\n"
    "- Strong hook (1-2 sentences, no throat-clearing)\n"
    "- A concrete story or example drawn from the material\n"
    "- 3-5 distilled lessons, each with a bolded one-line takeaway\n"
    "- Heavy use of short paragraphs and bullet points for skimmability\n"
    "- A single, clear closing takeaway\n\n"
    "Do not introduce claims that aren't grounded in the material above. "
    "Cite the episode (and speaker/timestamp when available)."
)


def _citation(result: SearchResult) -> str:
    document = result.document
    citation = f"{document.episode}"
    # See rag_skill._citation — episode titles already carry the guest name,
    # so the speaker suffix would duplicate it.
    if document.speaker and document.speaker not in document.episode:
        citation += f" — {document.speaker}"
    if document.timestamp_range:
        citation += f" [{document.timestamp_range}]"
    return citation


def write_ship30_essay(topic: str, retrieve_context: RetrieveContextUseCase) -> dict:
    context = retrieve_context.execute(topic, top_k=SHIP30_TOP_K)

    if not context.found:
        return {
            "found": False,
            "topic": topic,
            "material": [],
            "citations": [],
            "guidance": (
                "No transcript material was found for this topic. Tell the user you "
                "couldn't find this in Lenny's transcripts. Do not write the essay "
                "from general knowledge."
            ),
        }

    material = [
        {"text": result.document.chunk, "citation": _citation(result), "episode": result.document.episode}
        for result in context.results
    ]
    citations = [item["citation"] for item in material]

    return {
        "found": True,
        "topic": topic,
        "material": material,
        "citations": citations,
        "guidance": SHIP30_GUIDANCE,
    }
