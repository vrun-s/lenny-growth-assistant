from datetime import datetime, timezone
from uuid import UUID, uuid4

import pytest

from app.application.use_cases.send_message import DUMMY_ASSISTANT_RESPONSE, SendMessageUseCase
from app.domain.entities.message import Message, MessageRole
from app.domain.entities.session import Session
from app.domain.exceptions import SessionNotFoundError
from app.domain.interfaces.repositories import IMessageRepository, ISessionRepository


class FakeSessionRepository(ISessionRepository):
    def __init__(self, sessions: dict[UUID, Session] | None = None) -> None:
        self.sessions = sessions or {}
        self.touched: list[UUID] = []

    def create(self, session: Session) -> Session:
        self.sessions[session.id] = session
        return session

    def get(self, session_id: UUID) -> Session | None:
        return self.sessions.get(session_id)

    def list(self) -> list[Session]:
        return list(self.sessions.values())

    def delete(self, session_id: UUID) -> bool:
        return self.sessions.pop(session_id, None) is not None

    def touch(self, session_id: UUID) -> None:
        self.touched.append(session_id)


class FakeMessageRepository(IMessageRepository):
    def __init__(self) -> None:
        self.messages: list[Message] = []

    def create(self, message: Message) -> Message:
        self.messages.append(message)
        return message

    def list_by_session(self, session_id: UUID) -> list[Message]:
        return [m for m in self.messages if m.session_id == session_id]


def _existing_session() -> Session:
    now = datetime.now(timezone.utc)
    return Session(id=uuid4(), title="Test session", created_at=now, updated_at=now)


def test_raises_session_not_found_for_missing_session():
    use_case = SendMessageUseCase(FakeMessageRepository(), FakeSessionRepository())

    with pytest.raises(SessionNotFoundError):
        use_case.execute(uuid4(), "hello")


def test_persists_user_and_assistant_messages():
    session = _existing_session()
    message_repo = FakeMessageRepository()
    session_repo = FakeSessionRepository({session.id: session})
    use_case = SendMessageUseCase(message_repo, session_repo)

    use_case.execute(session.id, "hello there")

    stored = message_repo.list_by_session(session.id)
    assert [m.role for m in stored] == [MessageRole.USER, MessageRole.ASSISTANT]
    assert stored[0].content == "hello there"
    assert stored[1].content == DUMMY_ASSISTANT_RESPONSE


def test_returns_the_persisted_assistant_message():
    session = _existing_session()
    session_repo = FakeSessionRepository({session.id: session})
    use_case = SendMessageUseCase(FakeMessageRepository(), session_repo)

    result = use_case.execute(session.id, "hello")

    assert result.role == MessageRole.ASSISTANT
    assert result.content == DUMMY_ASSISTANT_RESPONSE
    assert result.id is not None
    assert result.created_at is not None


def test_touches_the_session():
    session = _existing_session()
    session_repo = FakeSessionRepository({session.id: session})
    use_case = SendMessageUseCase(FakeMessageRepository(), session_repo)

    use_case.execute(session.id, "hello")

    assert session_repo.touched == [session.id]


def test_does_not_persist_messages_for_a_missing_session():
    message_repo = FakeMessageRepository()
    use_case = SendMessageUseCase(message_repo, FakeSessionRepository())

    with pytest.raises(SessionNotFoundError):
        use_case.execute(uuid4(), "hello")

    assert message_repo.messages == []
