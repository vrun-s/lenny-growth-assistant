from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from uuid import UUID


class ArtifactType(str, Enum):
    MARKDOWN = "markdown"
    HTML = "html"


@dataclass
class Artifact:
    id: UUID
    session_id: UUID
    type: ArtifactType
    content: str
    created_at: datetime
