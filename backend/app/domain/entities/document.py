from dataclasses import dataclass
from uuid import UUID


@dataclass
class Document:
    id: UUID
    title: str
    source: str
    episode: str
    chunk: str
    embedding: list[float]
    speaker: str | None = None
    timestamp_range: str | None = None
