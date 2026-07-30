"""Groups parsed transcript segments into bounded-size chunks, generating a
stable chunk ID per chunk (uuid5 over source + chunk index) so re-ingesting
the same source is idempotent — the same source produces the same IDs, and
IngestDocumentsUseCase's dedup/PgVectorStore's upsert rely on that.
"""

import uuid

from app.domain.entities.document import Document
from app.infrastructure.ingestion.parser import ParsedTranscript, TranscriptSegment

CHUNK_ID_NAMESPACE = uuid.UUID("5f8e6f0e-6b1a-4a2e-9c1d-9b6f2e6a4d10")
DEFAULT_MAX_CHUNK_CHARS = 1000


def _stable_chunk_id(source: str, chunk_index: int) -> uuid.UUID:
    return uuid.uuid5(CHUNK_ID_NAMESPACE, f"{source}#{chunk_index}")


def _timestamp_range(segments: list[TranscriptSegment]) -> str | None:
    timestamps = [s.timestamp for s in segments if s.timestamp]
    if not timestamps:
        return None
    return timestamps[0] if len(timestamps) == 1 else f"{timestamps[0]}–{timestamps[-1]}"


def _speaker(segments: list[TranscriptSegment]) -> str | None:
    speakers = {s.speaker for s in segments if s.speaker}
    return next(iter(speakers)) if len(speakers) == 1 else None


def chunk_transcript(
    transcript: ParsedTranscript,
    episode: str,
    *,
    max_chunk_chars: int = DEFAULT_MAX_CHUNK_CHARS,
) -> list[Document]:
    documents: list[Document] = []
    current: list[TranscriptSegment] = []
    current_chars = 0
    chunk_index = 0

    def flush() -> None:
        nonlocal current, current_chars, chunk_index
        if not current:
            return
        documents.append(
            Document(
                id=_stable_chunk_id(transcript.source, chunk_index),
                title=transcript.title,
                source=transcript.source,
                episode=episode,
                chunk="\n".join(s.text for s in current),
                speaker=_speaker(current),
                timestamp_range=_timestamp_range(current),
            )
        )
        chunk_index += 1
        current = []
        current_chars = 0

    for segment in transcript.segments:
        if current_chars + len(segment.text) > max_chunk_chars and current:
            flush()
        current.append(segment)
        current_chars += len(segment.text)

    flush()
    return documents
