from app.domain.entities.document import Document
from app.domain.interfaces.vectorstore import IVectorStore


class IngestDocumentsUseCase:
    """Enforces chunk integrity (non-empty text, no duplicate IDs within a
    batch) before handing documents to the vector store, which owns embedding
    and persistence. Ports only — no parser/chunker/embedder import.
    """

    def __init__(self, vectorstore: IVectorStore) -> None:
        self._vectorstore = vectorstore

    def execute(self, documents: list[Document]) -> int:
        if not documents:
            return 0

        seen_ids: set = set()
        deduped: list[Document] = []
        for document in documents:
            if not document.chunk.strip():
                raise ValueError(f"Document {document.id} has empty chunk text")
            if document.id in seen_ids:
                continue
            seen_ids.add(document.id)
            deduped.append(document)

        self._vectorstore.add_documents(deduped)
        return len(deduped)
