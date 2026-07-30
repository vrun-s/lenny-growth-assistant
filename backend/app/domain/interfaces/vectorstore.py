from abc import ABC, abstractmethod

from app.domain.entities.document import Document
from app.domain.entities.search_result import SearchResult


class IVectorStore(ABC):
    """Vector index port. Embedding generation is an implementation detail of
    the adapter (see infrastructure/vectorstore/embeddings.py) — callers never
    handle raw embedding vectors, only Documents and text queries (matches the
    existing note on Document.embedding: retrieval has no reason to carry a
    768-float vector back up through the layers).
    """

    @abstractmethod
    def add_documents(self, documents: list[Document]) -> None:
        """Persist documents, embedding any that don't already carry a vector."""
        ...

    @abstractmethod
    def search(self, query: str, top_k: int = 5) -> list[SearchResult]:
        """Embed the query and return up to top_k documents ranked by similarity,
        highest first. Returns an empty list if nothing is relevant — callers
        must not treat that as an error.
        """
        ...
