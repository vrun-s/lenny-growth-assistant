from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from app.domain.entities.session import Session


class SessionCreateRequest(BaseModel):
    title: str | None = None


class SessionResponse(BaseModel):
    id: UUID
    title: str
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_entity(cls, session: Session) -> "SessionResponse":
        return cls(
            id=session.id,
            title=session.title,
            created_at=session.created_at,
            updated_at=session.updated_at,
        )
