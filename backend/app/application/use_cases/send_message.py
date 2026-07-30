from datetime import datetime, timezone
from uuid import UUID, uuid4

from app.domain.entities.message import Message, MessageRole
from app.domain.exceptions import SessionNotFoundError
from app.domain.interfaces.repositories import IMessageRepository, ISessionRepository

DUMMY_ASSISTANT_RESPONSE = "This is a dummy response."


class SendMessageUseCase:
    def __init__(self, message_repo: IMessageRepository, session_repo: ISessionRepository) -> None:
        self._message_repo = message_repo
        self._session_repo = session_repo

    def execute(self, session_id: UUID, message: str) -> Message:
        if self._session_repo.get(session_id) is None:
            raise SessionNotFoundError(session_id)

        self._message_repo.create(
            Message(
                id=uuid4(),
                session_id=session_id,
                role=MessageRole.USER,
                content=message,
                created_at=datetime.now(timezone.utc),
            )
        )

        assistant_message = self._message_repo.create(
            Message(
                id=uuid4(),
                session_id=session_id,
                role=MessageRole.ASSISTANT,
                content=DUMMY_ASSISTANT_RESPONSE,
                created_at=datetime.now(timezone.utc),
            )
        )

        self._session_repo.touch(session_id)

        return assistant_message
