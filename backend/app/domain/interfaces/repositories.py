from abc import ABC, abstractmethod
from uuid import UUID

from app.domain.entities.message import Message
from app.domain.entities.session import Session


class ISessionRepository(ABC):
    @abstractmethod
    def create(self, session: Session) -> Session: ...

    @abstractmethod
    def get(self, session_id: UUID) -> Session | None: ...

    @abstractmethod
    def list(self) -> list[Session]: ...

    @abstractmethod
    def delete(self, session_id: UUID) -> bool:
        """Delete the session, returning True if it existed."""
        ...


class IMessageRepository(ABC):
    @abstractmethod
    def create(self, message: Message) -> Message: ...

    @abstractmethod
    def list_by_session(self, session_id: UUID) -> list[Message]: ...
