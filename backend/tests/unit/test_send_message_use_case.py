import asyncio
from datetime import datetime, timezone
from uuid import UUID, uuid4

import pytest

from app.application.use_cases.send_message import SendMessageUseCase
from app.domain.entities.agent_result import AgentResult
from app.domain.entities.message import Message, MessageRole
from app.domain.entities.session import Session
from app.domain.entities.stream_chunk import StreamChunk
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

    def rename(self, session_id: UUID, title: str) -> Session | None:
        session = self.sessions.get(session_id)
        if session is None:
            return None
        session.title = title
        return session


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

    async def run_stream(self, history: list[Message], user_message: str, session_id: UUID):
        yield StreamChunk(kind="final", result=self.run(history, user_message, session_id))


class ScriptedStreamHarness(IAgentHarness):
    """Yields a fixed, pre-scripted sequence of StreamChunks — for testing
    SendMessageUseCase.execute_stream's persistence behavior in isolation
    from any real SDK streaming mechanics (those are AgentSdkHarness's job,
    verified live per docs/agent-transcripts/build-log.md).
    """

    def __init__(self, chunks: list[StreamChunk]) -> None:
        self._chunks = chunks

    def run(self, history: list[Message], user_message: str, session_id: UUID) -> AgentResult:
        raise NotImplementedError

    async def run_stream(self, history: list[Message], user_message: str, session_id: UUID):
        for chunk in self._chunks:
            yield chunk


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


def test_persists_citations_onto_the_assistant_message():
    session = _existing_session()
    message_repo = FakeMessageRepository()
    session_repo = FakeSessionRepository({session.id: session})
    harness = FakeAgentHarness()
    harness.run = lambda history, user_message, session_id: AgentResult(  # type: ignore[method-assign]
        text=FAKE_ASSISTANT_RESPONSE, citations=["Annie Duke — Decision Making"]
    )
    use_case = SendMessageUseCase(message_repo, session_repo, harness)

    use_case.execute(session.id, "hello")

    stored = message_repo.list_by_session(session.id)
    assert stored[0].citations == []
    assert stored[1].citations == ["Annie Duke — Decision Making"]


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


def test_execute_stream_raises_session_not_found_for_missing_session():
    use_case = SendMessageUseCase(FakeMessageRepository(), FakeSessionRepository(), ScriptedStreamHarness([]))

    async def run():
        async for _ in use_case.execute_stream(uuid4(), "hello"):
            pass

    with pytest.raises(SessionNotFoundError):
        asyncio.run(run())


def test_execute_stream_persists_user_message_immediately():
    session = _existing_session()
    message_repo = FakeMessageRepository()
    session_repo = FakeSessionRepository({session.id: session})
    chunks = [StreamChunk(kind="text", text="hi"), StreamChunk(kind="final", result=AgentResult(text="hi"))]
    use_case = SendMessageUseCase(message_repo, session_repo, ScriptedStreamHarness(chunks))

    async def run():
        return [c async for c in use_case.execute_stream(session.id, "hello there")]

    asyncio.run(run())

    stored = message_repo.list_by_session(session.id)
    assert stored[0].role == MessageRole.USER
    assert stored[0].content == "hello there"


def test_execute_stream_persists_assistant_message_and_citations_on_final_chunk():
    session = _existing_session()
    message_repo = FakeMessageRepository()
    session_repo = FakeSessionRepository({session.id: session})
    chunks = [
        StreamChunk(kind="text", text="Hello"),
        StreamChunk(kind="text", text=" world"),
        StreamChunk(kind="tool_call", tool_name="rag_query"),
        StreamChunk(kind="final", result=AgentResult(text="Hello world", citations=["Ep 1 — Lenny"])),
    ]
    use_case = SendMessageUseCase(message_repo, session_repo, ScriptedStreamHarness(chunks))

    async def run():
        return [c async for c in use_case.execute_stream(session.id, "hi")]

    received = asyncio.run(run())

    assert received == chunks
    stored = message_repo.list_by_session(session.id)
    assert [m.role for m in stored] == [MessageRole.USER, MessageRole.ASSISTANT]
    assert stored[1].content == "Hello world"
    assert stored[1].citations == ["Ep 1 — Lenny"]
    assert session_repo.touched == [session.id]


def test_execute_stream_persists_partial_text_plus_marker_on_error_chunk():
    session = _existing_session()
    message_repo = FakeMessageRepository()
    session_repo = FakeSessionRepository({session.id: session})
    chunks = [
        StreamChunk(kind="text", text="Partial answer"),
        StreamChunk(kind="error", error="Local model didn't respond — is Ollama running?"),
    ]
    use_case = SendMessageUseCase(message_repo, session_repo, ScriptedStreamHarness(chunks))

    async def run():
        return [c async for c in use_case.execute_stream(session.id, "hi")]

    asyncio.run(run())

    stored = message_repo.list_by_session(session.id)
    assert stored[1].content.startswith("Partial answer")
    assert "interrupted" in stored[1].content.lower()


def test_execute_stream_persists_interrupted_marker_with_no_partial_text():
    session = _existing_session()
    message_repo = FakeMessageRepository()
    session_repo = FakeSessionRepository({session.id: session})
    chunks = [StreamChunk(kind="error", error="Local model didn't respond — is Ollama running?")]
    use_case = SendMessageUseCase(message_repo, session_repo, ScriptedStreamHarness(chunks))

    async def run():
        return [c async for c in use_case.execute_stream(session.id, "hi")]

    asyncio.run(run())

    stored = message_repo.list_by_session(session.id)
    assert stored[1].content == "_[Response was interrupted]_"


def test_execute_stream_persists_partial_text_if_client_disconnects_before_final():
    """Simulates a real client disconnect: the caller (the SSE route's
    generator) stops iterating and closes the generator before a "final" or
    "error" chunk ever arrives — PRD §7.1's "never fail silently" applies
    here too, not just to explicit error chunks.
    """
    session = _existing_session()
    message_repo = FakeMessageRepository()
    session_repo = FakeSessionRepository({session.id: session})
    chunks = [
        StreamChunk(kind="text", text="partial"),
        StreamChunk(kind="text", text=" text"),
        StreamChunk(kind="final", result=AgentResult(text="never reached")),
    ]
    use_case = SendMessageUseCase(message_repo, session_repo, ScriptedStreamHarness(chunks))

    async def run():
        gen = use_case.execute_stream(session.id, "hi")
        await gen.__anext__()  # consume exactly one chunk, then abandon
        await gen.aclose()

    asyncio.run(run())

    stored = message_repo.list_by_session(session.id)
    assert stored[1].content.startswith("partial")
    assert "interrupted" in stored[1].content.lower()
    assert stored[1].content != "never reached"
