"""Integration tests against a real Postgres+pgvector instance. pgvector's
`vector` column type has no SQLite equivalent (unlike the rest of this
project's SQLite-backed test suite), so these tests need the real
docker-compose database and skip cleanly when it isn't reachable rather than
failing the whole suite.
"""

from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.exc import OperationalError

from app.core.config import get_settings
from app.domain.entities.document import Document
from app.infrastructure.vectorstore.pgvector_store import DocumentModel, PgVectorStore, _VectorBase


class FakeEmbedder:
    """Deterministic stand-in for OllamaEmbedder — no network call, no Ollama
    dependency. Embeds by hashing the text into a fixed-length vector so
    similar/dissimilar inputs still produce distinguishable vectors.
    """

    def embed(self, text: str) -> list[float]:
        seed = sum(ord(c) for c in text)
        return [((seed + i) % 97) / 97 for i in range(768)]


@pytest.fixture
def store():
    settings = get_settings()
    try:
        candidate = PgVectorStore(embedder=FakeEmbedder(), database_url=settings.database_url)
        with candidate._engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except OperationalError:
        pytest.skip("Postgres/pgvector not reachable — start `docker compose up -d` to run this test")

    _VectorBase.metadata.create_all(candidate._engine)
    try:
        with candidate._session_factory() as session:
            session.query(DocumentModel).delete()
            session.commit()
        yield candidate
    finally:
        with candidate._session_factory() as session:
            session.query(DocumentModel).delete()
            session.commit()


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
