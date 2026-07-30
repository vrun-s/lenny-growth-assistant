from datetime import datetime, timezone
from uuid import UUID, uuid4

import pytest

from app.application.use_cases.send_message import SendMessageUseCase
from app.domain.entities.agent_result import AgentResult
from app.domain.entities.message import Message, MessageRole
from app.domain.entities.session import Session
from app.domain.exceptions import SessionNotFoundError
from app.domain.interfaces.agent_harness import IAgentHarness
from app.domain.interfaces.repositories import IMessageRepository, ISessionRepository

FAKE_ASSISTANT_RESPONSE = "This is a fake harness response."


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


class FakeAgentHarness(IAgentHarness):
    def __init__(self, response_text: str = FAKE_ASSISTANT_RESPONSE) -> None:
        self.response_text = response_text
        self.calls: list[tuple[list[Message], str, UUID]] = []

    def run(self, history: list[Message], user_message: str, session_id: UUID) -> AgentResult:
        self.calls.append((history, user_message, session_id))
        return AgentResult(text=self.response_text)


def _existing_session() -> Session:
    now = datetime.now(timezone.utc)
    return Session(id=uuid4(), title="Test session", created_at=now, updated_at=now)


def test_raises_session_not_found_for_missing_session():
    use_case = SendMessageUseCase(FakeMessageRepository(), FakeSessionRepository(), FakeAgentHarness())

    with pytest.raises(SessionNotFoundError):
        use_case.execute(uuid4(), "hello")


def test_persists_user_and_assistant_messages():
    session = _existing_session()
    message_repo = FakeMessageRepository()
    session_repo = FakeSessionRepository({session.id: session})
    use_case = SendMessageUseCase(message_repo, session_repo, FakeAgentHarness())

    use_case.execute(session.id, "hello there")

    stored = message_repo.list_by_session(session.id)
    assert [m.role for m in stored] == [MessageRole.USER, MessageRole.ASSISTANT]
    assert stored[0].content == "hello there"
    assert stored[1].content == FAKE_ASSISTANT_RESPONSE


def test_returns_the_harness_result():
    session = _existing_session()
    session_repo = FakeSessionRepository({session.id: session})
    use_case = SendMessageUseCase(FakeMessageRepository(), session_repo, FakeAgentHarness())

    result = use_case.execute(session.id, "hello")

    assert result.text == FAKE_ASSISTANT_RESPONSE


def test_touches_the_session():
    session = _existing_session()
    session_repo = FakeSessionRepository({session.id: session})
    use_case = SendMessageUseCase(FakeMessageRepository(), session_repo, FakeAgentHarness())

    use_case.execute(session.id, "hello")

    assert session_repo.touched == [session.id]


def test_does_not_persist_messages_for_a_missing_session():
    message_repo = FakeMessageRepository()
    use_case = SendMessageUseCase(message_repo, FakeSessionRepository(), FakeAgentHarness())

    with pytest.raises(SessionNotFoundError):
        use_case.execute(uuid4(), "hello")

    assert message_repo.messages == []


def test_harness_receives_prior_history_not_including_the_new_message():
    session = _existing_session()
    message_repo = FakeMessageRepository()
    session_repo = FakeSessionRepository({session.id: session})
    harness = FakeAgentHarness()
    use_case = SendMessageUseCase(message_repo, session_repo, harness)

    use_case.execute(session.id, "first")
    use_case.execute(session.id, "second")

    first_call_history, first_call_message, _ = harness.calls[0]
    second_call_history, second_call_message, _ = harness.calls[1]

    assert first_call_history == []
    assert first_call_message == "first"
    assert [m.content for m in second_call_history] == ["first", FAKE_ASSISTANT_RESPONSE]
    assert second_call_message == "second"
