from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class SessionCreateRequest(BaseModel):
    title: str | None = None


class SessionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    created_at: datetime
    updated_at: datetime
