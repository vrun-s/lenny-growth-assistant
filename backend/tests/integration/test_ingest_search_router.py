from uuid import uuid4

from fastapi.testclient import TestClient
import pytest

from app.domain.entities.document import Document
from app.domain.entities.search_result import SearchResult
from app.domain.interfaces.vectorstore import IVectorStore
from app.infrastructure.api.app import create_app
from app.infrastructure.api.deps import get_vector_store


class FakeVectorStore(IVectorStore):
    def __init__(self) -> None:
        self.added: list[Document] = []
        self.next_results: list[SearchResult] = []

    def add_documents(self, documents: list[Document]) -> None:
        self.added.extend(documents)

    def search(self, query: str, top_k: int = 5) -> list[SearchResult]:
        return self.next_results[:top_k]


@pytest.fixture
def vectorstore() -> FakeVectorStore:
    return FakeVectorStore()


@pytest.fixture
def client(vectorstore: FakeVectorStore) -> TestClient:
    app = create_app()
    app.dependency_overrides[get_vector_store] = lambda: vectorstore
    return TestClient(app)


TRANSCRIPT = """# Growth Loops 101

**[00:00:12] Lenny:** Growth loops beat funnels for compounding acquisition.
"""


def test_ingest_returns_chunk_count(client: TestClient):
    response = client.post("/api/ingest", json={"markdown": TRANSCRIPT, "source": "ep01.md"})

    assert response.status_code == 200
    body = response.json()
    assert body["title"] == "Growth Loops 101"
    assert body["source"] == "ep01.md"
    assert body["ingested_chunks"] == 1


def test_ingest_persists_documents_via_the_vectorstore_port(client: TestClient, vectorstore: FakeVectorStore):
    client.post("/api/ingest", json={"markdown": TRANSCRIPT, "source": "ep01.md"})

    assert len(vectorstore.added) == 1
    assert vectorstore.added[0].speaker == "Lenny"


def test_search_returns_ranked_results(client: TestClient, vectorstore: FakeVectorStore):
    document = Document(
        id=uuid4(),
        title="Growth Loops 101",
        source="ep01.md",
        episode="Ep 1",
        chunk="Growth loops beat funnels.",
        speaker="Lenny",
    )
    vectorstore.next_results = [SearchResult(document=document, score=0.87)]

    response = client.post("/api/search", json={"query": "growth loops", "top_k": 3})

    assert response.status_code == 200
    body = response.json()
    assert body["found"] is True
    assert body["results"][0]["score"] == 0.87
    assert body["results"][0]["speaker"] == "Lenny"


def test_search_with_no_results_reports_not_found(client: TestClient):
    response = client.post("/api/search", json={"query": "nothing relevant"})

    assert response.status_code == 200
    body = response.json()
    assert body["found"] is False
    assert body["results"] == []
