from app.domain.entities.session import Session
from app.domain.interfaces.repositories import ISessionRepository


class ListSessionsUseCase:
    def __init__(self, session_repo: ISessionRepository) -> None:
        self._session_repo = session_repo

    def execute(self) -> list[Session]:
        return self._session_repo.list()
