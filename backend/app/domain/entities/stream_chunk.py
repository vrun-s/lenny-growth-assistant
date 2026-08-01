from dataclasses import dataclass
from typing import Literal

from app.domain.entities.agent_result import AgentResult

StreamChunkKind = Literal["text", "tool_call", "final", "error"]


@dataclass
class StreamChunk:
    """One increment of a streaming turn (IAgentHarness.run_stream). Keeps SDK
    stream-event shapes out of the inner layers, same reasoning as AgentResult
    for the non-streaming path.

    - "text": a token delta to append to the in-progress assistant message.
    - "tool_call": a tool started executing (name only — no args, the
      frontend only needs this to show a "using <tool>..." indicator).
    - "final": the turn is done. Carries the same shape POST /api/chat
      already returns (full text, citations, artifact) so the frontend
      renders sources/artifact card only once, at the end.
    - "error": the turn failed or was interrupted (timeout, harness error).
    """

    kind: StreamChunkKind
    text: str | None = None
    tool_name: str | None = None
    result: AgentResult | None = None
    error: str | None = None
