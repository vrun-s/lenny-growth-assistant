import json
from collections.abc import AsyncIterator
from typing import Any
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends
from fastapi.responses import StreamingResponse

from app.application.use_cases.auto_name_session import AutoNameSessionUseCase
from app.application.use_cases.send_message import SendMessageUseCase
from app.domain.entities.stream_chunk import StreamChunk
from app.domain.exceptions import SessionNotFoundError
from app.domain.interfaces.agent_harness import IAgentHarness
from app.domain.interfaces.repositories import IMessageRepository, ISessionRepository
from app.infrastructure.api.deps import get_agent_harness, get_message_repository, get_session_repository
from app.infrastructure.api.v1.schemas import ChatRequest, ChatResponse

router = APIRouter(prefix="/chat", tags=["chat"])


def _run_auto_name(
    session_id: UUID,
    session_repo: ISessionRepository,
    message_repo: IMessageRepository,
    harness: IAgentHarness,
) -> None:
    """Scheduled via BackgroundTasks so it runs after the response (or, for
    the streaming route, the SSE body) has already gone to the client —
    Feature 4 must never add visible latency to the actual conversation.
    AutoNameSessionUseCase no-ops unless this really was the first exchange
    and the session still has its placeholder title, so scheduling it after
    every turn (not just detectably-first ones) is harmless.
    """
    AutoNameSessionUseCase(session_repo, message_repo, harness).execute(session_id)


@router.post("", response_model=ChatResponse)
def send_message(
    payload: ChatRequest,
    background_tasks: BackgroundTasks,
    message_repo: IMessageRepository = Depends(get_message_repository),
    session_repo: ISessionRepository = Depends(get_session_repository),
    harness: IAgentHarness = Depends(get_agent_harness),
) -> ChatResponse:
    use_case = SendMessageUseCase(message_repo, session_repo, harness)
    result = use_case.execute(payload.session_id, payload.message)
    background_tasks.add_task(_run_auto_name, payload.session_id, session_repo, message_repo, harness)
    return ChatResponse(
        session_id=payload.session_id,
        assistant_message=result.text,
        citations=result.citations,
        artifact_id=result.artifact.id if result.artifact else None,
    )


def _serialize_chunk(chunk: StreamChunk) -> str:
    """SSE framing (`data: {...}\\n\\n`). Plain dict + json.dumps rather than
    a Pydantic response model — StreamingResponse bypasses FastAPI's
    response_model machinery entirely, so a full schema class would buy
    nothing here.
    """
    payload: dict[str, Any]
    if chunk.kind == "text":
        payload = {"kind": "text", "text": chunk.text}
    elif chunk.kind == "tool_call":
        payload = {"kind": "tool_call", "tool_name": chunk.tool_name}
    elif chunk.kind == "final":
        result = chunk.result
        payload = {
            "kind": "final",
            "assistant_message": result.text if result else "",
            "citations": result.citations if result else [],
            "artifact_id": str(result.artifact.id) if result and result.artifact else None,
        }
    else:  # "error"
        payload = {"kind": "error", "error": chunk.error}
    return f"data: {json.dumps(payload)}\n\n"


@router.post("/stream")
async def send_message_stream(
    payload: ChatRequest,
    background_tasks: BackgroundTasks,
    message_repo: IMessageRepository = Depends(get_message_repository),
    session_repo: ISessionRepository = Depends(get_session_repository),
    harness: IAgentHarness = Depends(get_agent_harness),
) -> StreamingResponse:
    # Checked here, not just inside the use case: once StreamingResponse
    # starts iterating its body, the 200 status line is already on the wire
    # (Starlette sends http.response.start before the first body chunk), so
    # a SessionNotFoundError raised from inside the generator could no
    # longer become a real 404 — this pre-check lets the existing
    # app-level exception handler produce the same 404 POST /api/chat
    # already returns for a missing session.
    if session_repo.get(payload.session_id) is None:
        raise SessionNotFoundError(payload.session_id)

    use_case = SendMessageUseCase(message_repo, session_repo, harness)

    async def event_stream() -> AsyncIterator[str]:
        try:
            async for chunk in use_case.execute_stream(payload.session_id, payload.message):
                yield _serialize_chunk(chunk)
        finally:
            # In a finally, not just after the loop, so this still fires if
            # the client disconnects mid-stream (GeneratorExit unwinds
            # through here too) — same "always schedule it, let the use
            # case's own guards decide whether to actually rename" reasoning
            # as the non-streaming route above.
            background_tasks.add_task(_run_auto_name, payload.session_id, session_repo, message_repo, harness)

    return StreamingResponse(event_stream(), media_type="text/event-stream", background=background_tasks)
