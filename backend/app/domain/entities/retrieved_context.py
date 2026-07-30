from dataclasses import dataclass

from app.domain.entities.search_result import SearchResult


@dataclass
class RetrievedContext:
    """Return type of RetrieveContextUseCase. `found` lets a caller (the future
    rag_skill) check for "nothing relevant" without special-casing an empty list —
    this is the "decline gracefully" contract required by PRD §7.1 / workflow.md
    Phase 4's grading criterion.
    """

    query: str
    results: list[SearchResult]

    @property
    def found(self) -> bool:
        return bool(self.results)
