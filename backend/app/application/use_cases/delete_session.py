from uuid import UUID

from app.domain.interfaces.repositories import ISessionRepository


class DeleteSessionUseCase:
    def __init__(self, session_repo: ISessionRepository) -> None:
        self._session_repo = session_repo

    def execute(self, session_id: UUID) -> bool:
        return self._session_repo.delete(session_id)
