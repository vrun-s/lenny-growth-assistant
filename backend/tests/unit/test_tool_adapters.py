import json
from uuid import uuid4

import pytest

from app.application.use_cases.retrieve_context import RetrieveContextUseCase
from app.domain.entities.artifact import ArtifactType
from app.domain.entities.document import Document
from app.domain.entities.search_result import SearchResult
from app.domain.interfaces.repositories import IArtifactRepository
from app.domain.interfaces.vectorstore import IVectorStore
from app.infrastructure.harness.tool_adapters import (
    ToolRunResults,
    handle_generate_artifact,
    handle_rag_query,
    handle_write_ship30_essay,
)


class FakeVectorStore(IVectorStore):
    def __init__(self, results: list[SearchResult] | None = None, error: Exception | None = None) -> None:
        self._results = results or []
        self._error = error

    def add_documents(self, documents: list[Document]) -> None:
        raise NotImplementedError

    def search(self, query: str, top_k: int = 5) -> list[SearchResult]:
        if self._error is not None:
            raise self._error
        return self._results[:top_k]


class FakeArtifactRepository(IArtifactRepository):
    def __init__(self, error: Exception | None = None) -> None:
        self.saved = []
        self._error = error

    def create(self, artifact):
        if self._error is not None:
            raise self._error
        self.saved.append(artifact)
        return artifact

    def get(self, artifact_id):
        return next((a for a in self.saved if a.id == artifact_id), None)


def _result(chunk: str, episode: str) -> SearchResult:
    document = Document(id=uuid4(), title="Title", source="s.md", episode=episode, chunk=chunk)
    return SearchResult(document=document, score=0.9)


@pytest.mark.anyio
async def test_rag_query_handler_returns_text_content_and_records_citations():
    retrieve_context = RetrieveContextUseCase(FakeVectorStore([_result("chunk", "Episode 1")]))
    results = ToolRunResults()

    response = await handle_rag_query(
        {"question": "what is retention?"}, retrieve_context=retrieve_context, results=results
    )

    assert response.get("is_error") is not True
    payload = json.loads(response["content"][0]["text"])
    assert payload["found"] is True
    assert results.citations == ["Episode 1"]


@pytest.mark.anyio
async def test_rag_query_handler_returns_tool_error_not_a_crash():
    retrieve_context = RetrieveContextUseCase(FakeVectorStore(error=RuntimeError("vectorstore down")))
    results = ToolRunResults()

    response = await handle_rag_query({"question": "x"}, retrieve_context=retrieve_context, results=results)

    assert response["is_error"] is True
    assert "vectorstore down" in response["content"][0]["text"]
    assert results.citations == []


@pytest.mark.anyio
async def test_ship30_handler_records_citations():
    retrieve_context = RetrieveContextUseCase(FakeVectorStore([_result("chunk", "Episode 2")]))
    results = ToolRunResults()

    response = await handle_write_ship30_essay(
        {"topic": "pricing"}, retrieve_context=retrieve_context, results=results
    )

    assert response.get("is_error") is not True
    assert results.citations == ["Episode 2"]


@pytest.mark.anyio
async def test_ship30_handler_returns_tool_error_not_a_crash():
    retrieve_context = RetrieveContextUseCase(FakeVectorStore(error=RuntimeError("timeout")))
    results = ToolRunResults()

    response = await handle_write_ship30_essay(
        {"topic": "pricing"}, retrieve_context=retrieve_context, results=results
    )

    assert response["is_error"] is True


@pytest.mark.anyio
async def test_generate_artifact_handler_persists_and_records_result():
    repo = FakeArtifactRepository()
    results = ToolRunResults()
    session_id = uuid4()

    response = await handle_generate_artifact(
        {"artifact_type": "markdown", "content": "# hi"},
        session_id=session_id,
        artifact_repo=repo,
        results=results,
    )

    assert response.get("is_error") is not True
    assert results.artifact is not None
    assert results.artifact.type == ArtifactType.MARKDOWN
    assert results.artifact.session_id == session_id
    assert len(repo.saved) == 1


@pytest.mark.anyio
async def test_generate_artifact_handler_returns_tool_error_for_invalid_type():
    repo = FakeArtifactRepository()
    results = ToolRunResults()

    response = await handle_generate_artifact(
        {"artifact_type": "pdf", "content": "x"},
        session_id=uuid4(),
        artifact_repo=repo,
        results=results,
    )

    assert response["is_error"] is True
    assert results.artifact is None
    assert repo.saved == []


@pytest.mark.anyio
async def test_generate_artifact_handler_returns_tool_error_on_repo_failure():
    repo = FakeArtifactRepository(error=RuntimeError("db down"))
    results = ToolRunResults()

    response = await handle_generate_artifact(
        {"artifact_type": "markdown", "content": "x"},
        session_id=uuid4(),
        artifact_repo=repo,
        results=results,
    )

    assert response["is_error"] is True
    assert results.artifact is None


def test_add_citations_deduplicates():
    results = ToolRunResults()

    results.add_citations(["Episode 1", "Episode 2"])
    results.add_citations(["Episode 1", "Episode 3"])

    assert results.citations == ["Episode 1", "Episode 2", "Episode 3"]
