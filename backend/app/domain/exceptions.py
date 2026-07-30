from uuid import UUID


class SessionNotFoundError(Exception):
    def __init__(self, session_id: UUID) -> None:
        super().__init__(f"Session {session_id} not found")
        self.session_id = session_id
