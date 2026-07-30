from app.domain.entities.retrieved_context import RetrievedContext
from app.domain.interfaces.vectorstore import IVectorStore

DEFAULT_TOP_K = 5
MAX_TOP_K = 20


class RetrieveContextUseCase:
    """Enforces the top_k bound and wraps IVectorStore.search's result in the
    RetrievedContext shape the future rag_skill (Phase 5) checks for grounding —
    not a passthrough: it's the single place the "decline gracefully when
    nothing is relevant" contract (PRD §7.1) is guaranteed for every caller.
    """

    def __init__(self, vectorstore: IVectorStore) -> None:
        self._vectorstore = vectorstore

    def execute(self, query: str, top_k: int = DEFAULT_TOP_K) -> RetrievedContext:
        bounded_top_k = max(1, min(top_k, MAX_TOP_K))
        results = self._vectorstore.search(query, top_k=bounded_top_k)
        return RetrievedContext(query=query, results=results)
