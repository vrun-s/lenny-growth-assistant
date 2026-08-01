from datetime import datetime, timezone
from uuid import UUID, uuid4

from app.application.use_cases.auto_name_session import AutoNameSessionUseCase
from app.application.use_cases.create_session import DEFAULT_TITLE
from app.domain.entities.agent_result import AgentResult
from app.domain.entities.message import Message, MessageRole
from app.domain.entities.session import Session
from app.domain.interfaces.agent_harness import IAgentHarness
from app.domain.interfaces.repositories import IMessageRepository, ISessionRepository


class FakeSessionRepository(ISessionRepository):
    def __init__(self, sessions: dict[UUID, Session]) -> None:
        self.sessions = sessions
        self.renamed: list[tuple[UUID, str]] = []

    def create(self, session: Session) -> Session:
        raise NotImplementedError

    def get(self, session_id: UUID) -> Session | None:
        return self.sessions.get(session_id)

    def list(self) -> list[Session]:
        return list(self.sessions.values())

    def delete(self, session_id: UUID) -> bool:
        raise NotImplementedError

    def touch(self, session_id: UUID) -> None:
        raise NotImplementedError

    def rename(self, session_id: UUID, title: str) -> Session | None:
        session = self.sessions.get(session_id)
        if session is None:
            return None
        session.title = title
        self.renamed.append((session_id, title))
        return session


class FakeMessageRepository(IMessageRepository):
    def __init__(self, messages: list[Message]) -> None:
        self._messages = messages

    def create(self, message: Message) -> Message:
        raise NotImplementedError

    def list_by_session(self, session_id: UUID) -> list[Message]:
        return [m for m in self._messages if m.session_id == session_id]


class FakeHarness(IAgentHarness):
    def __init__(self, response_text: str = "Growth Loops Explained") -> None:
        self.response_text = response_text
        self.calls = 0

    def run(self, history, user_message, session_id) -> AgentResult:
        self.calls += 1
        return AgentResult(text=self.response_text)

    async def run_stream(self, history, user_message, session_id):
        raise NotImplementedError


class RaisingHarness(IAgentHarness):
    def run(self, history, user_message, session_id) -> AgentResult:
        raise RuntimeError("harness unavailable")

    async def run_stream(self, history, user_message, session_id):
        raise NotImplementedError


def _session(title: str = DEFAULT_TITLE) -> Session:
    now = datetime.now(timezone.utc)
    return Session(id=uuid4(), title=title, created_at=now, updated_at=now)


def _first_exchange_messages(session_id: UUID) -> list[Message]:
    now = datetime.now(timezone.utc)
    return [
        Message(id=uuid4(), session_id=session_id, role=MessageRole.USER, content="What is a growth loop?", created_at=now),
        Message(
            id=uuid4(),
            session_id=session_id,
            role=MessageRole.ASSISTANT,
            content="A growth loop is a self-reinforcing cycle that drives user acquisition.",
            created_at=now,
        ),
    ]


def test_renames_session_using_generated_title_after_first_exchange():
    session = _session()
    session_repo = FakeSessionRepository({session.id: session})
    message_repo = FakeMessageRepository(_first_exchange_messages(session.id))
    harness = FakeHarness("Growth Loops Explained")

    AutoNameSessionUseCase(session_repo, message_repo, harness).execute(session.id)

    assert session_repo.renamed == [(session.id, "Growth Loops Explained")]


def test_does_not_fire_when_session_already_has_more_than_two_messages():
    session = _session()
    session_repo = FakeSessionRepository({session.id: session})
    messages = _first_exchange_messages(session.id) * 2  # 4 messages -> not the first exchange anymore
    message_repo = FakeMessageRepository(messages)
    harness = FakeHarness()

    AutoNameSessionUseCase(session_repo, message_repo, harness).execute(session.id)

    assert session_repo.renamed == []
    assert harness.calls == 0


def test_does_not_overwrite_a_manual_rename():
    session = _session(title="My custom title")
    session_repo = FakeSessionRepository({session.id: session})
    message_repo = FakeMessageRepository(_first_exchange_messages(session.id))
    harness = FakeHarness()

    AutoNameSessionUseCase(session_repo, message_repo, harness).execute(session.id)

    assert session_repo.renamed == []
    assert harness.calls == 0


def test_falls_back_to_truncated_user_message_when_harness_fails():
    session = _session()
    session_repo = FakeSessionRepository({session.id: session})
    message_repo = FakeMessageRepository(_first_exchange_messages(session.id))

    AutoNameSessionUseCase(session_repo, message_repo, RaisingHarness()).execute(session.id)

    assert session_repo.renamed == [(session.id, "What is a growth loop?")]


def test_falls_back_to_truncation_when_generated_title_is_empty():
    session = _session()
    session_repo = FakeSessionRepository({session.id: session})
    message_repo = FakeMessageRepository(_first_exchange_messages(session.id))
    harness = FakeHarness("   ")

    AutoNameSessionUseCase(session_repo, message_repo, harness).execute(session.id)

    assert session_repo.renamed == [(session.id, "What is a growth loop?")]


def test_falls_back_to_truncation_when_generated_title_is_too_long():
    session = _session()
    session_repo = FakeSessionRepository({session.id: session})
    message_repo = FakeMessageRepository(_first_exchange_messages(session.id))
    harness = FakeHarness("x" * 200)

    AutoNameSessionUseCase(session_repo, message_repo, harness).execute(session.id)

    assert session_repo.renamed == [(session.id, "What is a growth loop?")]


def test_truncation_fallback_adds_ellipsis_for_long_messages():
    session = _session()
    session_repo = FakeSessionRepository({session.id: session})
    long_message = "A" * 100
    now = datetime.now(timezone.utc)
    messages = [
        Message(id=uuid4(), session_id=session.id, role=MessageRole.USER, content=long_message, created_at=now),
        Message(id=uuid4(), session_id=session.id, role=MessageRole.ASSISTANT, content="reply", created_at=now),
    ]
    message_repo = FakeMessageRepository(messages)

    AutoNameSessionUseCase(session_repo, message_repo, RaisingHarness()).execute(session.id)

    _, title = session_repo.renamed[0]
    assert title.endswith("…")
    assert len(title) <= 48


def test_strips_surrounding_quotes_from_generated_title():
    session = _session()
    session_repo = FakeSessionRepository({session.id: session})
    message_repo = FakeMessageRepository(_first_exchange_messages(session.id))
    harness = FakeHarness('"Growth Loops Explained"')

    AutoNameSessionUseCase(session_repo, message_repo, harness).execute(session.id)

    assert session_repo.renamed == [(session.id, "Growth Loops Explained")]


def test_noop_for_missing_session():
    session_repo = FakeSessionRepository({})
    message_repo = FakeMessageRepository([])
    harness = FakeHarness()

    AutoNameSessionUseCase(session_repo, message_repo, harness).execute(uuid4())

    assert session_repo.renamed == []
    assert harness.calls == 0
