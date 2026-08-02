import asyncio
import logging
from collections.abc import AsyncIterator
from uuid import UUID

from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    ClaudeSDKClient,
    ResultMessage,
    StreamEvent,
    TextBlock,
    ToolUseBlock,
)

from app.application.use_cases.retrieve_context import RetrieveContextUseCase
from app.core.config import Settings, get_settings
from app.core.runtime import SUBPROCESS_UNSUPPORTED_MESSAGE, event_loop_supports_subprocess
from app.domain.entities.agent_result import AgentResult
from app.domain.entities.message import Message, MessageRole
from app.domain.entities.stream_chunk import StreamChunk
from app.domain.exceptions import HarnessUnavailableError
from app.domain.interfaces.agent_harness import IAgentHarness
from app.domain.interfaces.repositories import IArtifactRepository
from app.infrastructure.harness.tool_adapters import ALLOWED_TOOLS, SERVER_NAME, ToolRunResults, build_tool_server

SYSTEM_PROMPT = (
    "You are a growth advisor grounded in Lenny's Podcast transcripts. "
    "Use the tools available to you to answer questions, write essays, and "
    "generate artifacts. Never answer product or growth questions from your "
    "own general knowledge — only from what your tools return."
)

# Bounds a runaway tool-call loop (PRD §7.1's "iteration cap prevents runaway
# loops"). Three tool calls plus a final composed reply comfortably covers
# the three registered tools; the SDK counts each side of a turn. Applies to
# both run() and run_stream() — streaming doesn't relax this.
MAX_TURNS = 8

logger = logging.getLogger(__name__)

_TOOL_NAME_PREFIX = f"mcp__{SERVER_NAME}__"


def _build_prompt(history: list[Message], user_message: str) -> str:
    speaker = {MessageRole.USER: "User", MessageRole.ASSISTANT: "Assistant"}
    turns = [f"{speaker[m.role]}: {m.content}" for m in history]
    turns.append(f"User: {user_message}")
    return "\n\n".join(turns)


def _strip_tool_prefix(name: str) -> str:
    return name.removeprefix(_TOOL_NAME_PREFIX)


class AgentSdkHarness(IAgentHarness):
    """The only IAgentHarness implementation (see docs/design.md and
    ARCHITECTURE.md §6). Wraps the Claude Agent SDK, which owns the agent
    loop. Registers the three domain tools built in
    infrastructure/harness/tool_adapters.py fresh on every turn, scoped to
    that turn's session_id and use cases.
    """

    def __init__(
        self,
        retrieve_context: RetrieveContextUseCase,
        artifact_repo: IArtifactRepository,
        settings: Settings | None = None,
    ) -> None:
        self._retrieve_context = retrieve_context
        self._artifact_repo = artifact_repo
        self._settings = settings or get_settings()

    def run(self, history: list[Message], user_message: str, session_id: UUID) -> AgentResult:
        try:
            return asyncio.run(
                asyncio.wait_for(
                    self._run_async(history, user_message, session_id),
                    timeout=self._settings.harness_timeout_seconds,
                )
            )
        except HarnessUnavailableError:
            raise
        except Exception as exc:
            # Mapping an exception to a user-facing string while discarding the
            # traceback is exactly the silent failure PRD §7.1 forbids — and is
            # what made the --reload diagnosis take hours (see build-log).
            logger.exception("Harness run() failed (provider=%s)", self._settings.llm_provider)
            raise HarnessUnavailableError(self._settings.llm_provider) from exc

    def _build_options(
        self, session_id: UUID, results: ToolRunResults, *, streaming: bool
    ) -> ClaudeAgentOptions:
        ### env: dict[str, str] = {} ##FOR LOCAL TESTING
        ### env = {"ANTHROPIC_API_KEY": self._settings.harness_api_key}  ##FOR GITHUB CHANGES

        env = {"ANTHROPIC_API_KEY": self._settings.harness_api_key}
        if self._settings.harness_base_url is not None:
            env["ANTHROPIC_BASE_URL"] = self._settings.harness_base_url

        tool_server = build_tool_server(
            retrieve_context=self._retrieve_context,
            artifact_repo=self._artifact_repo,
            session_id=session_id,
            results=results,
        )

        options = ClaudeAgentOptions(
            system_prompt=SYSTEM_PROMPT,
            model=self._settings.harness_model,
            env=env,
            mcp_servers={SERVER_NAME: tool_server},
            allowed_tools=ALLOWED_TOOLS,
            # Disable the Claude Code CLI's own built-in tool belt (Bash, Edit,
            # Read, ...) — this is a growth advisor, not a coding agent; it must
            # only ever reach the three domain tools registered above.
            tools=[],
            # There's no human in the loop to answer a permission prompt for our
            # own registered tools, so a non-default permission_mode would hang
            # every tool call forever.
            permission_mode="bypassPermissions",
            max_turns=MAX_TURNS,
        )
        if streaming:
            # Emits StreamEvent (raw Anthropic content_block_delta events)
            # alongside the existing complete AssistantMessage/ResultMessage
            # types — verified via inspect.getsource(ClaudeAgentOptions) /
            # message_parser.py, not assumed. Off by default for run() since
            # the non-streaming path has no use for token-level deltas.
            options.include_partial_messages = True
        if self._settings.llm_provider == "ollama":
            # Local reasoning models (e.g. qwen3) otherwise emit very long
            # chain-of-thought before any answer, which is prohibitively slow
            # on CPU — see docs/agent-transcripts/build-log.md.
            options.thinking = {"type": "disabled"}
        return options

    async def _run_async(
        self, history: list[Message], user_message: str, session_id: UUID
    ) -> AgentResult:
        results = ToolRunResults()
        options = self._build_options(session_id, results, streaming=False)
        prompt = _build_prompt(history, user_message)
        text_parts: list[str] = []

        async with ClaudeSDKClient(options=options) as client:
            await client.query(prompt)
            async for message in client.receive_response():
                if isinstance(message, AssistantMessage):
                    for block in message.content:
                        if isinstance(block, TextBlock):
                            text_parts.append(block.text)
                elif isinstance(message, ResultMessage) and message.is_error:
                    raise HarnessUnavailableError(self._settings.llm_provider)

        return AgentResult(
            text="".join(text_parts),
            citations=results.citations,
            artifact=results.artifact,
        )

    async def run_stream(
        self, history: list[Message], user_message: str, session_id: UUID
    ) -> AsyncIterator[StreamChunk]:
        """Same agent loop as run()/_run_async(), un-buffered: yields a
        StreamChunk per token delta and per tool call started, instead of
        accumulating silently and returning once the whole turn is done.
        Never raises — a failure or timeout becomes a terminal "error"
        StreamChunk, since raising out of an async generator mid-stream would
        leave the SSE route with nothing to send the client (PRD §7.1: never
        fail silently, and don't just hang the connection either).
        """
        results = ToolRunResults()
        text_parts: list[str] = []
        loop = asyncio.get_event_loop()
        deadline = loop.time() + self._settings.harness_timeout_seconds

        # Checked up front rather than left to fail inside the SDK: the CLI
        # subprocess spawn would otherwise surface as a bare CLIConnectionError
        # and get mapped to "Local model didn't respond — is Ollama running?",
        # which sends whoever is debugging it after Ollama instead of the
        # actual cause (--reload on Windows). run() is deliberately not
        # guarded — it calls asyncio.run(), which builds its own loop.
        if not event_loop_supports_subprocess():
            yield StreamChunk(kind="error", error=SUBPROCESS_UNSUPPORTED_MESSAGE)
            return

        try:
            options = self._build_options(session_id, results, streaming=True)
            prompt = _build_prompt(history, user_message)

            async with ClaudeSDKClient(options=options) as client:
                await client.query(prompt)
                response_iter = client.receive_response()
                while True:
                    remaining = deadline - loop.time()
                    if remaining <= 0:
                        raise TimeoutError
                    try:
                        message = await asyncio.wait_for(response_iter.__anext__(), timeout=remaining)
                    except StopAsyncIteration:
                        break

                    if isinstance(message, StreamEvent):
                        delta = message.event.get("delta", {})
                        if message.event.get("type") == "content_block_delta" and delta.get("type") == "text_delta":
                            text = delta.get("text", "")
                            if text:
                                yield StreamChunk(kind="text", text=text)
                    elif isinstance(message, AssistantMessage):
                        for block in message.content:
                            if isinstance(block, TextBlock):
                                text_parts.append(block.text)
                            elif isinstance(block, ToolUseBlock):
                                yield StreamChunk(kind="tool_call", tool_name=_strip_tool_prefix(block.name))
                    elif isinstance(message, ResultMessage):
                        if message.is_error:
                            raise HarnessUnavailableError(self._settings.llm_provider)
                        break
        except TimeoutError:
            logger.warning(
                "Harness run_stream() timed out after %ss (provider=%s)",
                self._settings.harness_timeout_seconds,
                self._settings.llm_provider,
            )
            yield StreamChunk(kind="error", error=str(HarnessUnavailableError(self._settings.llm_provider)))
            return
        except HarnessUnavailableError as exc:
            logger.exception("Harness run_stream() reported an error result")
            yield StreamChunk(kind="error", error=str(exc))
            return
        except Exception:
            logger.exception(
                "Harness run_stream() failed (provider=%s)", self._settings.llm_provider
            )
            yield StreamChunk(kind="error", error=str(HarnessUnavailableError(self._settings.llm_provider)))
            return

        yield StreamChunk(
            kind="final",
            result=AgentResult(text="".join(text_parts), citations=results.citations, artifact=results.artifact),
        )
