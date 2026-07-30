from dataclasses import dataclass

from app.domain.entities.document import Document


@dataclass
class SearchResult:
    """A single retrieved chunk plus its similarity score, ranked highest-first."""

    document: Document
    score: float
