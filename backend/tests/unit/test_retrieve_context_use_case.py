from uuid import uuid4

from app.application.use_cases.retrieve_context import MAX_TOP_K, RetrieveContextUseCase
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


def _result(score: float) -> SearchResult:
    document = Document(id=uuid4(), title="Title", source="s.md", episode="Ep 1", chunk="chunk")
    return SearchResult(document=document, score=score)


def test_returns_found_true_when_results_exist():
    vectorstore = FakeVectorStore([_result(0.9)])
    use_case = RetrieveContextUseCase(vectorstore)

    context = use_case.execute("what is a growth loop?")

    assert context.found is True
    assert len(context.results) == 1


def test_returns_found_false_when_nothing_relevant():
    vectorstore = FakeVectorStore([])
    use_case = RetrieveContextUseCase(vectorstore)

    context = use_case.execute("something not in the corpus")

    assert context.found is False
    assert context.results == []


def test_clamps_top_k_to_maximum():
    vectorstore = FakeVectorStore([])
    use_case = RetrieveContextUseCase(vectorstore)

    use_case.execute("query", top_k=1000)

    assert vectorstore.last_top_k == MAX_TOP_K


def test_clamps_top_k_to_minimum_of_one():
    vectorstore = FakeVectorStore([])
    use_case = RetrieveContextUseCase(vectorstore)

    use_case.execute("query", top_k=0)

    assert vectorstore.last_top_k == 1


def test_preserves_the_query_on_the_result():
    vectorstore = FakeVectorStore([])
    use_case = RetrieveContextUseCase(vectorstore)

    context = use_case.execute("growth loops")

    assert context.query == "growth loops"
