import asyncio
from uuid import UUID

from claude_agent_sdk import AssistantMessage, ClaudeAgentOptions, ClaudeSDKClient, ResultMessage, TextBlock

from app.application.use_cases.retrieve_context import RetrieveContextUseCase
from app.core.config import Settings, get_settings
from app.domain.entities.agent_result import AgentResult
from app.domain.entities.message import Message, MessageRole
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
# the three registered tools; the SDK counts each side of a turn.
MAX_TURNS = 8


def _build_prompt(history: list[Message], user_message: str) -> str:
    speaker = {MessageRole.USER: "User", MessageRole.ASSISTANT: "Assistant"}
    turns = [f"{speaker[m.role]}: {m.content}" for m in history]
    turns.append(f"User: {user_message}")
    return "\n\n".join(turns)


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
            raise HarnessUnavailableError(self._settings.llm_provider) from exc

    async def _run_async(
        self, history: list[Message], user_message: str, session_id: UUID
    ) -> AgentResult:
        env = {"ANTHROPIC_API_KEY": self._settings.harness_api_key}
        if self._settings.harness_base_url is not None:
            env["ANTHROPIC_BASE_URL"] = self._settings.harness_base_url

        results = ToolRunResults()
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
        if self._settings.llm_provider == "ollama":
            # Local reasoning models (e.g. qwen3) otherwise emit very long
            # chain-of-thought before any answer, which is prohibitively slow
            # on CPU — see docs/agent-transcripts/build-log.md.
            options.thinking = {"type": "disabled"}

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
