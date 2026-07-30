from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass
class Session:
    id: UUID
    title: str
    created_at: datetime
    updated_at: datetime
