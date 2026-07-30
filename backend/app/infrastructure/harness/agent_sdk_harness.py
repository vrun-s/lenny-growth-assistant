import asyncio

from claude_agent_sdk import AssistantMessage, ClaudeAgentOptions, ClaudeSDKClient, ResultMessage, TextBlock

from app.core.config import Settings, get_settings
from app.domain.entities.agent_result import AgentResult
from app.domain.entities.message import Message, MessageRole
from app.domain.exceptions import HarnessUnavailableError
from app.domain.interfaces.agent_harness import IAgentHarness

SYSTEM_PROMPT = (
    "You are a growth advisor grounded in Lenny's Podcast transcripts. "
    "Use the tools available to you to answer questions, write essays, and "
    "generate artifacts. Never answer product or growth questions from your "
    "own general knowledge — only from what your tools return."
)


def _build_prompt(history: list[Message], user_message: str) -> str:
    speaker = {MessageRole.USER: "User", MessageRole.ASSISTANT: "Assistant"}
    turns = [f"{speaker[m.role]}: {m.content}" for m in history]
    turns.append(f"User: {user_message}")
    return "\n\n".join(turns)


class AgentSdkHarness(IAgentHarness):
    """The only IAgentHarness implementation (see docs/design.md and
    ARCHITECTURE.md §6). Wraps the Claude Agent SDK, which owns the agent
    loop. No tools are registered yet — tool registration is added in
    infrastructure/harness/tool_adapters.py once the skills in
    application/skills/ have real bodies.
    """

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()

    def run(self, history: list[Message], user_message: str) -> AgentResult:
        try:
            return asyncio.run(
                asyncio.wait_for(
                    self._run_async(history, user_message),
                    timeout=self._settings.harness_timeout_seconds,
                )
            )
        except HarnessUnavailableError:
            raise
        except Exception as exc:
            raise HarnessUnavailableError(self._settings.llm_provider) from exc

    async def _run_async(self, history: list[Message], user_message: str) -> AgentResult:
        env = {"ANTHROPIC_API_KEY": self._settings.harness_api_key}
        if self._settings.harness_base_url is not None:
            env["ANTHROPIC_BASE_URL"] = self._settings.harness_base_url

        options = ClaudeAgentOptions(
            system_prompt=SYSTEM_PROMPT,
            model=self._settings.harness_model,
            env=env,
        )

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

        return AgentResult(text="".join(text_parts))
