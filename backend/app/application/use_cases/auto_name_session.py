import logging
from uuid import UUID

from app.application.use_cases.create_session import DEFAULT_TITLE
from app.domain.interfaces.agent_harness import IAgentHarness
from app.domain.interfaces.repositories import IMessageRepository, ISessionRepository

logger = logging.getLogger(__name__)

# Deliberately not the main chat SYSTEM_PROMPT (AgentSdkHarness.SYSTEM_PROMPT
# tells the model to only answer from tools, grounded in the transcripts) —
# this is a meta-task about the conversation itself, not a growth question,
# so it's framed as a distinct instruction via the user turn rather than
# widening IAgentHarness.run()'s signature with a system-prompt parameter
# just for this one background caller.
#
# Verified live against Anthropic: an earlier version opened with "Ignore
# any earlier instructions..." — Claude (correctly) treated that as a
# prompt-injection pattern, refused the meta-task, and answered the embedded
# question instead, which the length/newline validation below caught and
# fell back to truncation for. Rephrased to ask for the title as its own
# legitimate request rather than an override, which stopped triggering that
# refusal — no "ignore/override/disregard" phrasing here.
_TITLE_PROMPT = (
    "A chat application needs a short sidebar title for the conversation below. "
    "Write ONLY that title (3-6 words, no quotes, no punctuation at the end, no "
    "commentary, no tool calls) — just the title text itself, nothing else.\n\n"
    "User: {user_message}\n"
    "Assistant: {assistant_message}"
)

_MAX_GENERATED_TITLE_LENGTH = 60
_TRUNCATED_TITLE_LENGTH = 47  # ~44 chars + an ellipsis, per the "~40-50 chars" spec


class AutoNameSessionUseCase:
    """Generates a short session title from the first exchange. Guards
    against firing more than once (only proceeds when the session has
    exactly the two messages a first exchange produces) and against
    overwriting a manual rename (only proceeds while the session still has
    its original placeholder title) — the simpler guard the task's own
    write-up allows in place of tracking rename-vs-autoname races explicitly.
    """

    def __init__(
        self,
        session_repo: ISessionRepository,
        message_repo: IMessageRepository,
        harness: IAgentHarness,
    ) -> None:
        self._session_repo = session_repo
        self._message_repo = message_repo
        self._harness = harness

    def execute(self, session_id: UUID) -> None:
        session = self._session_repo.get(session_id)
        if session is None or session.title != DEFAULT_TITLE:
            return

        messages = self._message_repo.list_by_session(session_id)
        if len(messages) != 2:
            return

        title = self._generate_title(session_id, messages[0].content, messages[1].content)
        self._session_repo.rename(session_id, title)

    def _generate_title(self, session_id: UUID, user_message: str, assistant_message: str) -> str:
        try:
            prompt = _TITLE_PROMPT.format(user_message=user_message, assistant_message=assistant_message)
            result = self._harness.run([], prompt, session_id)
            candidate = result.text.strip().strip('"').strip("'").strip()
            if candidate and "\n" not in candidate and len(candidate) <= _MAX_GENERATED_TITLE_LENGTH:
                return candidate
            logger.info("Auto-name title looked unusable, falling back to truncation: %r", candidate)
        except Exception:
            logger.exception("Auto-name harness call failed, falling back to truncation")
        return self._truncate(user_message)

    @staticmethod
    def _truncate(text: str) -> str:
        stripped = text.strip()
        if not stripped:
            return DEFAULT_TITLE
        if len(stripped) <= _TRUNCATED_TITLE_LENGTH:
            return stripped
        return stripped[:_TRUNCATED_TITLE_LENGTH].rstrip() + "…"
