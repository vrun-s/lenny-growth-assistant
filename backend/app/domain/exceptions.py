from uuid import UUID


class SessionNotFoundError(Exception):
    def __init__(self, session_id: UUID) -> None:
        super().__init__(f"Session {session_id} not found")
        self.session_id = session_id


class HarnessUnavailableError(Exception):
    """The agent harness could not complete a turn (unreachable provider, timeout).

    `message` overrides the provider-derived default for failures that aren't
    the provider's fault — currently the Windows `--reload` incompatibility
    (see app/core/runtime.py), where blaming Ollama actively misleads whoever
    is debugging it. Kept as one exception type with one 502 mapping rather
    than a second class, since the handling is identical either way.
    """

    def __init__(self, provider: str, message: str | None = None) -> None:
        if message is None:
            message = (
                "Local model didn't respond — is Ollama running?"
                if provider == "ollama"
                else "The AI provider didn't respond. Please try again shortly."
            )
        super().__init__(message)
        self.provider = provider
