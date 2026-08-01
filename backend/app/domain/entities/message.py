from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from uuid import UUID


class MessageRole(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"


@dataclass
class Message:
    id: UUID
    session_id: UUID
    role: MessageRole
    content: str
    created_at: datetime
    artifact_id: UUID | None = None
    citations: list[str] = field(default_factory=list)
