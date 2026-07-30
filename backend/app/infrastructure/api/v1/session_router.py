from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from app.application.use_cases.create_session import CreateSessionUseCase
from app.application.use_cases.delete_session import DeleteSessionUseCase
from app.application.use_cases.list_sessions import ListSessionsUseCase
from app.domain.interfaces.repositories import ISessionRepository
from app.infrastructure.api.deps import get_session_repository
from app.infrastructure.api.v1.schemas import SessionCreateRequest, SessionResponse

router = APIRouter(prefix="/sessions", tags=["sessions"])


@router.post("", response_model=SessionResponse, status_code=status.HTTP_201_CREATED)
def create_session(
    payload: SessionCreateRequest = SessionCreateRequest(),
    session_repo: ISessionRepository = Depends(get_session_repository),
) -> SessionResponse:
    use_case = CreateSessionUseCase(session_repo)
    session = use_case.execute(title=payload.title)
    return SessionResponse.from_entity(session)


@router.get("", response_model=list[SessionResponse])
def list_sessions(
    session_repo: ISessionRepository = Depends(get_session_repository),
) -> list[SessionResponse]:
    use_case = ListSessionsUseCase(session_repo)
    sessions = use_case.execute()
    return [SessionResponse.from_entity(session) for session in sessions]


@router.delete("/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_session(
    session_id: UUID,
    session_repo: ISessionRepository = Depends(get_session_repository),
) -> None:
    use_case = DeleteSessionUseCase(session_repo)
    deleted = use_case.execute(session_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
