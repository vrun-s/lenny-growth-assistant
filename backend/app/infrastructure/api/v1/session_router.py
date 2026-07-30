from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from app.application.use_cases.create_session import CreateSessionUseCase
from app.domain.interfaces.repositories import IMessageRepository, ISessionRepository
from app.infrastructure.api.deps import get_message_repository, get_session_repository
from app.infrastructure.api.v1.schemas import (
    MessageResponse,
    SessionCreateRequest,
    SessionResponse,
    SessionWithMessagesResponse,
)

router = APIRouter(prefix="/sessions", tags=["sessions"])


@router.post("", response_model=SessionResponse, status_code=status.HTTP_201_CREATED)
def create_session(
    payload: SessionCreateRequest | None = None,
    session_repo: ISessionRepository = Depends(get_session_repository),
) -> SessionResponse:
    use_case = CreateSessionUseCase(session_repo)
    session = use_case.execute(title=payload.title if payload else None)
    return SessionResponse.model_validate(session)


@router.get("", response_model=list[SessionResponse])
def list_sessions(
    session_repo: ISessionRepository = Depends(get_session_repository),
) -> list[SessionResponse]:
    return [SessionResponse.model_validate(session) for session in session_repo.list()]


@router.get("/{session_id}", response_model=SessionWithMessagesResponse)
def get_session(
    session_id: UUID,
    session_repo: ISessionRepository = Depends(get_session_repository),
    message_repo: IMessageRepository = Depends(get_message_repository),
) -> SessionWithMessagesResponse:
    session = session_repo.get(session_id)
    if session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    messages = message_repo.list_by_session(session_id)
    return SessionWithMessagesResponse(
        session=SessionResponse.model_validate(session),
        messages=[MessageResponse.model_validate(message) for message in messages],
    )


@router.delete("/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_session(
    session_id: UUID,
    session_repo: ISessionRepository = Depends(get_session_repository),
) -> None:
    if not session_repo.delete(session_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
