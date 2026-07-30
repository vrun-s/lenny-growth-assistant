"""Thin orchestration of parser.py + chunker.py — the single ingestion-side
entrypoint the composition layer (scripts/run_ingestion.py, the /api/ingest
router) calls, so neither has to know the parse-then-chunk sequence itself.

No vectorstore import here: infrastructure sub-modules must not import one
another directly (ARCHITECTURE.md §2.2). Handing this function's output to
IngestDocumentsUseCase is the composition layer's job, not this module's.
"""

from app.domain.entities.document import Document
from app.infrastructure.ingestion.chunker import chunk_transcript
from app.infrastructure.ingestion.parser import parse_markdown_transcript


def load_transcript(
    markdown: str, *, episode: str | None = None, default_source: str = ""
) -> list[Document]:
    transcript = parse_markdown_transcript(markdown, default_source=default_source)
    return chunk_transcript(transcript, episode=episode or transcript.title)
