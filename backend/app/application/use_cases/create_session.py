from datetime import datetime, timezone
from uuid import uuid4

from app.domain.entities.session import Session
from app.domain.interfaces.repositories import ISessionRepository

DEFAULT_TITLE = "New chat"


class CreateSessionUseCase:
    def __init__(self, session_repo: ISessionRepository) -> None:
        self._session_repo = session_repo

    def execute(self, title: str | None = None) -> Session:
        now = datetime.now(timezone.utc)
        session = Session(
            id=uuid4(),
            title=title or DEFAULT_TITLE,
            created_at=now,
            updated_at=now,
        )
        return self._session_repo.create(session)
