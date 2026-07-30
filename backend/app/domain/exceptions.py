from uuid import UUID


class SessionNotFoundError(Exception):
    def __init__(self, session_id: UUID) -> None:
        super().__init__(f"Session {session_id} not found")
        self.session_id = session_id


class HarnessUnavailableError(Exception):
    """The agent harness could not complete a turn (unreachable provider, timeout)."""

    def __init__(self, provider: str) -> None:
        message = (
            "Local model didn't respond — is Ollama running?"
            if provider == "ollama"
            else "The AI provider didn't respond. Please try again shortly."
        )
        super().__init__(message)
        self.provider = provider
