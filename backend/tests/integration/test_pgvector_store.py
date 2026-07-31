"""Integration tests against a real Postgres+pgvector instance. pgvector's
`vector` column type has no SQLite equivalent (unlike the rest of this
project's SQLite-backed test suite), so these tests need the real
docker-compose database and skip cleanly when it isn't reachable rather than
failing the whole suite.

Isolation: `store` binds to the `pg_connection` fixture (backend/tests/conftest.py),
which runs against TEST_DATABASE_URL inside a transaction that's rolled back
after the test — never the development database, and never a `DELETE` that
could wipe real ingested data.
"""

from uuid import uuid4

import pytest
from sqlalchemy.engine import Connection

from app.domain.entities.document import Document
from app.infrastructure.vectorstore.pgvector_store import DocumentModel, PgVectorStore


class FakeEmbedder:
    """Deterministic stand-in for OllamaEmbedder — no network call, no Ollama
    dependency. Embeds by hashing the text into a fixed-length vector so
    similar/dissimilar inputs still produce distinguishable vectors.
    """

    def embed(self, text: str) -> list[float]:
        seed = sum(ord(c) for c in text)
        return [((seed + i) % 97) / 97 for i in range(768)]


@pytest.fixture
def store(pg_connection: Connection) -> PgVectorStore:
    return PgVectorStore(embedder=FakeEmbedder(), engine=pg_connection)


def _document(chunk: str, doc_id=None) -> Document:
    return Document(id=doc_id or uuid4(), title="Title", source="s.md", episode="Ep 1", chunk=chunk)


def test_add_then_search_returns_the_inserted_document(store: PgVectorStore):
    document = _document("Growth loops compound acquisition over time.")
    store.add_documents([document])

    results = store.search("growth loops", top_k=5)

    assert any(r.document.id == document.id for r in results)


def test_search_ranks_more_similar_text_higher(store: PgVectorStore):
    close = _document("Growth loops compound acquisition over time.")
    far = _document("Zzyzx qwerty unrelated filler text about nothing.")
    store.add_documents([close, far])

    results = store.search("Growth loops compound acquisition over time.", top_k=2)

    assert results[0].document.id == close.id


def test_search_with_no_documents_returns_empty(store: PgVectorStore):
    results = store.search("anything", top_k=5)

    assert results == []


def test_add_documents_is_idempotent_on_repeated_ingestion(store: PgVectorStore):
    doc_id = uuid4()
    store.add_documents([_document("first version", doc_id=doc_id)])
    store.add_documents([_document("second version", doc_id=doc_id)])

    with store._session_factory() as session:
        rows = session.query(DocumentModel).filter_by(id=doc_id).all()

    assert len(rows) == 1
    assert rows[0].chunk == "second version"
