from collections.abc import AsyncIterator
from datetime import datetime, timezone
from uuid import UUID, uuid4

from app.domain.entities.agent_result import AgentResult
from app.domain.entities.message import Message, MessageRole
from app.domain.entities.stream_chunk import StreamChunk
from app.domain.exceptions import SessionNotFoundError
from app.domain.interfaces.agent_harness import IAgentHarness
from app.domain.interfaces.repositories import IMessageRepository, ISessionRepository

# Shown when a streamed turn is cut off (harness error, timeout, or the
# client disconnecting mid-stream) with no usable text generated yet — PRD
# §7.1's "never fail silently": a session reload must never show a user
# message with no reply at all.
INTERRUPTED_MARKER = "_[Response was interrupted]_"


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
                citations=result.citations,
            )
        )

        self._session_repo.touch(session_id)

        return result

    async def execute_stream(self, session_id: UUID, message: str) -> AsyncIterator[StreamChunk]:
        """Streaming counterpart to execute(). The user message is saved
        immediately, same as the non-streaming path. The assistant message
        can't be saved until the full text is known — one coherent Message
        row per turn, not a row per token delta — so it's saved when the
        harness's "final" StreamChunk arrives. If the stream ends any other
        way (an "error" chunk, an unexpected exception, or the caller
        abandoning the generator because the client disconnected), the
        `finally` block persists whatever partial text was generated instead
        of silently dropping the exchange.
        """
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

        text_parts: list[str] = []
        assistant_message_persisted = False
        try:
            async for chunk in self._harness.run_stream(history, message, session_id):
                if chunk.kind == "text" and chunk.text:
                    text_parts.append(chunk.text)
                yield chunk
                if chunk.kind == "final" and chunk.result is not None:
                    self._persist_assistant_message(session_id, chunk.result)
                    assistant_message_persisted = True
                elif chunk.kind == "error":
                    self._persist_interrupted(session_id, text_parts)
                    assistant_message_persisted = True
        finally:
            if not assistant_message_persisted:
                self._persist_interrupted(session_id, text_parts)

    def _persist_assistant_message(self, session_id: UUID, result: AgentResult) -> None:
        self._message_repo.create(
            Message(
                id=uuid4(),
                session_id=session_id,
                role=MessageRole.ASSISTANT,
                content=result.text,
                created_at=datetime.now(timezone.utc),
                artifact_id=result.artifact.id if result.artifact else None,
                citations=result.citations,
            )
        )
        self._session_repo.touch(session_id)

    def _persist_interrupted(self, session_id: UUID, text_parts: list[str]) -> None:
        partial_text = "".join(text_parts).strip()
        content = f"{partial_text}\n\n{INTERRUPTED_MARKER}" if partial_text else INTERRUPTED_MARKER
        self._message_repo.create(
            Message(
                id=uuid4(),
                session_id=session_id,
                role=MessageRole.ASSISTANT,
                content=content,
                created_at=datetime.now(timezone.utc),
            )
        )
        self._session_repo.touch(session_id)
