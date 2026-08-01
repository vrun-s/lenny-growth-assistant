from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from uuid import UUID

from app.domain.entities.agent_result import AgentResult
from app.domain.entities.message import Message
from app.domain.entities.stream_chunk import StreamChunk


class IAgentHarness(ABC):
    """The single port through which a use case reaches a model. Replaces the
    cancelled ILLMProvider abstraction — there is no per-vendor provider class,
    only this one port plus config (see docs/design.md).
    """

    @abstractmethod
    def run(self, history: list[Message], user_message: str, session_id: UUID) -> AgentResult:
        """Run one turn: prior messages plus the new user message in, an
        AgentResult out. Implementations own the agent loop; this port does not.

        `session_id` is additive (Phase 4B, tool registration) — the
        generate_artifact tool must tie a persisted Artifact to the calling
        session, and the harness has no other way to learn it. Extending the
        port here, rather than smuggling session_id through some other
        channel, follows CLAUDE.md's "ports before adapters" rule.
        """
        ...

    @abstractmethod
    def run_stream(
        self, history: list[Message], user_message: str, session_id: UUID
    ) -> AsyncIterator[StreamChunk]:
        """Run one turn, yielding StreamChunks as the model produces them
        instead of returning a single AgentResult once the whole turn is
        done. Additive alongside `run()` (same pattern as `session_id` being
        added to `run()` in Phase 4B) — not a replacement; `run()` stays for
        callers that don't need incremental output (e.g. Feature 4's
        auto-naming call). Implementations still own the whole agent loop;
        this port does not.
        """
        ...
