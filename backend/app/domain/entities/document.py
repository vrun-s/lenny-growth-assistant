from dataclasses import dataclass
from uuid import UUID


@dataclass
class Document:
    id: UUID
    title: str
    source: str
    episode: str
    chunk: str
    speaker: str | None = None
    timestamp_range: str | None = None
    # Only populated during ingestion. Retrieval returns documents for citation
    # and has no reason to carry a 768-float vector back up through the layers.
    embedding: list[float] | None = None
