from datetime import datetime, timezone
from uuid import UUID, uuid4

from app.domain.entities.agent_result import AgentResult
from app.domain.entities.message import Message, MessageRole
from app.domain.exceptions import SessionNotFoundError
from app.domain.interfaces.agent_harness import IAgentHarness
from app.domain.interfaces.repositories import IMessageRepository, ISessionRepository


class SendMessageUseCase:
    def __init__(
        self,
        message_repo: IMessageRepository,
        session_repo: ISessionRepository,
        harness: IAgentHarness,
    ) -> None:
        self._message_repo = message_repo
        self._session_repo = session_repo
        self._harness = harness

    def execute(self, session_id: UUID, message: str) -> AgentResult:
        if self._session_repo.get(session_id) is None:
            raise SessionNotFoundError(session_id)

        history = self._message_repo.list_by_session(session_id)

        self._message_repo.create(
            Message(
                id=uuid4(),
                session_id=session_id,
                role=MessageRole.USER,
                content=message,
                created_at=datetime.now(timezone.utc),
            )
        )

        result = self._harness.run(history, message, session_id)

        self._message_repo.create(
            Message(
                id=uuid4(),
                session_id=session_id,
                role=MessageRole.ASSISTANT,
                content=result.text,
                created_at=datetime.now(timezone.utc),
                artifact_id=result.artifact.id if result.artifact else None,
            )
        )

        self._session_repo.touch(session_id)

        return result
