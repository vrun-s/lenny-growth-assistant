from fastapi import APIRouter, Depends

from app.application.use_cases.send_message import SendMessageUseCase
from app.domain.interfaces.agent_harness import IAgentHarness
from app.domain.interfaces.repositories import IMessageRepository, ISessionRepository
from app.infrastructure.api.deps import get_agent_harness, get_message_repository, get_session_repository
from app.infrastructure.api.v1.schemas import ChatRequest, ChatResponse

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("", response_model=ChatResponse)
def send_message(
    payload: ChatRequest,
    message_repo: IMessageRepository = Depends(get_message_repository),
    session_repo: ISessionRepository = Depends(get_session_repository),
    harness: IAgentHarness = Depends(get_agent_harness),
) -> ChatResponse:
    use_case = SendMessageUseCase(message_repo, session_repo, harness)
    result = use_case.execute(payload.session_id, payload.message)
    return ChatResponse(session_id=payload.session_id, assistant_message=result.text)
