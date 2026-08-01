from abc import ABC, abstractmethod
from uuid import UUID

from app.domain.entities.artifact import Artifact
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

    @abstractmethod
    def touch(self, session_id: UUID) -> None:
        """Bump the session's updated_at to now."""
        ...

    @abstractmethod
    def rename(self, session_id: UUID, title: str) -> Session | None:
        """Update the session's title (and bump updated_at, since a rename
        is itself an update). Returns the updated Session, or None if the
        session doesn't exist."""
        ...


class IMessageRepository(ABC):
    @abstractmethod
    def create(self, message: Message) -> Message: ...

    @abstractmethod
    def list_by_session(self, session_id: UUID) -> list[Message]: ...


class IArtifactRepository(ABC):
    @abstractmethod
    def create(self, artifact: Artifact) -> Artifact: ...

    @abstractmethod
    def get(self, artifact_id: UUID) -> Artifact | None: ...
