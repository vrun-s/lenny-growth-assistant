from uuid import uuid4

import pytest

from app.application.use_cases.ingest_documents import IngestDocumentsUseCase
from app.domain.entities.document import Document
from app.domain.entities.search_result import SearchResult
from app.domain.interfaces.vectorstore import IVectorStore


class FakeVectorStore(IVectorStore):
    def __init__(self) -> None:
        self.added: list[Document] = []

    def add_documents(self, documents: list[Document]) -> None:
        self.added.extend(documents)

    def search(self, query: str, top_k: int = 5) -> list[SearchResult]:
        return []


def _document(chunk: str = "some text", doc_id=None) -> Document:
    return Document(
        id=doc_id or uuid4(),
        title="Title",
        source="source.md",
        episode="Ep 1",
        chunk=chunk,
    )


def test_ingests_all_documents():
    vectorstore = FakeVectorStore()
    use_case = IngestDocumentsUseCase(vectorstore)

    count = use_case.execute([_document(), _document()])

    assert count == 2
    assert len(vectorstore.added) == 2


def test_empty_batch_is_a_no_op():
    vectorstore = FakeVectorStore()
    use_case = IngestDocumentsUseCase(vectorstore)

    count = use_case.execute([])

    assert count == 0
    assert vectorstore.added == []


def test_rejects_documents_with_empty_chunk_text():
    vectorstore = FakeVectorStore()
    use_case = IngestDocumentsUseCase(vectorstore)

    with pytest.raises(ValueError, match="empty chunk"):
        use_case.execute([_document(chunk="   ")])


def test_deduplicates_documents_by_id_within_a_batch():
    vectorstore = FakeVectorStore()
    use_case = IngestDocumentsUseCase(vectorstore)
    shared_id = uuid4()

    count = use_case.execute([_document(doc_id=shared_id), _document(doc_id=shared_id)])

    assert count == 1
    assert len(vectorstore.added) == 1
