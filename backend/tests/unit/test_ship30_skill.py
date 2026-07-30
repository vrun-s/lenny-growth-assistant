from uuid import uuid4

from app.application.skills.ship30_skill import SHIP30_TOP_K, write_ship30_essay
from app.application.use_cases.retrieve_context import RetrieveContextUseCase
from app.domain.entities.document import Document
from app.domain.entities.search_result import SearchResult
from app.domain.interfaces.vectorstore import IVectorStore


class FakeVectorStore(IVectorStore):
    def __init__(self, results: list[SearchResult]) -> None:
        self._results = results
        self.last_top_k: int | None = None

    def add_documents(self, documents: list[Document]) -> None:
        raise NotImplementedError

    def search(self, query: str, top_k: int = 5) -> list[SearchResult]:
        self.last_top_k = top_k
        return self._results[:top_k]


def _result(chunk: str, episode: str) -> SearchResult:
    document = Document(id=uuid4(), title="Title", source="s.md", episode=episode, chunk=chunk)
    return SearchResult(document=document, score=0.9)


def test_returns_not_found_when_nothing_relevant():
    retrieve_context = RetrieveContextUseCase(FakeVectorStore([]))

    result = write_ship30_essay("pricing", retrieve_context)

    assert result == {"found": False, "topic": "pricing", "material": [], "citations": []}


def test_retrieves_a_broader_top_k_than_the_default():
    vectorstore = FakeVectorStore([])
    retrieve_context = RetrieveContextUseCase(vectorstore)

    write_ship30_essay("pricing", retrieve_context)

    assert vectorstore.last_top_k == SHIP30_TOP_K


def test_returns_material_and_citations_when_found():
    results = [_result("Pricing is a signal.", "Episode 3")]
    retrieve_context = RetrieveContextUseCase(FakeVectorStore(results))

    result = write_ship30_essay("pricing", retrieve_context)

    assert result["found"] is True
    assert result["topic"] == "pricing"
    assert result["material"][0]["text"] == "Pricing is a signal."
    assert result["material"][0]["episode"] == "Episode 3"
    assert result["citations"] == ["Episode 3"]
