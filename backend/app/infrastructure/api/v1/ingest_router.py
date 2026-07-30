from fastapi import APIRouter, Depends

from app.application.use_cases.ingest_documents import IngestDocumentsUseCase
from app.domain.interfaces.vectorstore import IVectorStore
from app.infrastructure.api.deps import get_vector_store
from app.infrastructure.api.v1.schemas import IngestRequest, IngestResponse
from app.infrastructure.ingestion.loader import load_transcript

router = APIRouter(prefix="/ingest", tags=["ingestion"])


@router.post("", response_model=IngestResponse)
def ingest_transcript(
    payload: IngestRequest,
    vectorstore: IVectorStore = Depends(get_vector_store),
) -> IngestResponse:
    documents = load_transcript(payload.markdown, episode=payload.episode, default_source=payload.source)
    use_case = IngestDocumentsUseCase(vectorstore)
    ingested = use_case.execute(documents)
    title = documents[0].title if documents else "Untitled Episode"
    source = documents[0].source if documents else payload.source
    return IngestResponse(title=title, source=source, ingested_chunks=ingested)
