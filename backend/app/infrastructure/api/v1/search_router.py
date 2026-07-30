from fastapi import APIRouter, Depends

from app.application.use_cases.retrieve_context import RetrieveContextUseCase
from app.domain.interfaces.vectorstore import IVectorStore
from app.infrastructure.api.deps import get_vector_store
from app.infrastructure.api.v1.schemas import SearchRequest, SearchResponse, SearchResultResponse

router = APIRouter(prefix="/search", tags=["search"])


@router.post("", response_model=SearchResponse)
def search(
    payload: SearchRequest,
    vectorstore: IVectorStore = Depends(get_vector_store),
) -> SearchResponse:
    use_case = RetrieveContextUseCase(vectorstore)
    context = use_case.execute(payload.query, top_k=payload.top_k)
    return SearchResponse(
        query=context.query,
        found=context.found,
        results=[
            SearchResultResponse(
                chunk=result.document.chunk,
                score=result.score,
                title=result.document.title,
                source=result.document.source,
                episode=result.document.episode,
                speaker=result.document.speaker,
                timestamp_range=result.document.timestamp_range,
            )
            for result in context.results
        ],
    )
