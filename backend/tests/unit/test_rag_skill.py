from uuid import uuid4

from app.application.skills.rag_skill import rag_query
from app.application.use_cases.retrieve_context import RetrieveContextUseCase
from app.domain.entities.document import Document
from app.domain.entities.search_result import SearchResult
from app.domain.interfaces.vectorstore import IVectorStore


class FakeVectorStore(IVectorStore):
    def __init__(self, results: list[SearchResult]) -> None:
        self._results = results

    def add_documents(self, documents: list[Document]) -> None:
        raise NotImplementedError

    def search(self, query: str, top_k: int = 5) -> list[SearchResult]:
        return self._results[:top_k]


def _result(chunk: str, episode: str, speaker: str | None = None, timestamp: str | None = None) -> SearchResult:
    document = Document(
        id=uuid4(),
        title="Title",
        source="s.md",
        episode=episode,
        chunk=chunk,
        speaker=speaker,
        timestamp_range=timestamp,
    )
    return SearchResult(document=document, score=0.9)


def test_returns_not_found_when_nothing_relevant():
    retrieve_context = RetrieveContextUseCase(FakeVectorStore([]))

    result = rag_query("what is a growth loop?", retrieve_context)

    assert result == {"found": False, "chunks": [], "citations": []}


def test_returns_chunks_and_citations_when_found():
    results = [_result("Growth loops compound.", "Episode 1", speaker="Lenny", timestamp="00:01:00")]
    retrieve_context = RetrieveContextUseCase(FakeVectorStore(results))

    result = rag_query("what is a growth loop?", retrieve_context)

    assert result["found"] is True
    assert result["chunks"][0]["text"] == "Growth loops compound."
    assert result["chunks"][0]["citation"] == "Episode 1 — Lenny [00:01:00]"
    assert result["citations"] == ["Episode 1 — Lenny [00:01:00]"]


def test_citation_omits_missing_speaker_and_timestamp():
    results = [_result("Plain chunk.", "Episode 2")]
    retrieve_context = RetrieveContextUseCase(FakeVectorStore(results))

    result = rag_query("question", retrieve_context)

    assert result["chunks"][0]["citation"] == "Episode 2"
