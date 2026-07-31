from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.domain.entities.artifact import ArtifactType
from app.domain.entities.message import MessageRole


class SessionCreateRequest(BaseModel):
    title: str | None = None


class SessionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    created_at: datetime
    updated_at: datetime


class MessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    session_id: UUID
    role: MessageRole
    content: str
    created_at: datetime
    artifact_id: UUID | None = None


class SessionWithMessagesResponse(BaseModel):
    session: SessionResponse
    messages: list[MessageResponse]


class ArtifactResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    session_id: UUID
    type: ArtifactType
    content: str
    created_at: datetime


class ChatRequest(BaseModel):
    session_id: UUID
    message: str


class ChatResponse(BaseModel):
    session_id: UUID
    assistant_message: str
    citations: list[str] = []
    artifact_id: UUID | None = None


class IngestRequest(BaseModel):
    markdown: str
    source: str = ""
    episode: str | None = None


class IngestResponse(BaseModel):
    title: str
    source: str
    ingested_chunks: int


class SearchRequest(BaseModel):
    query: str
    top_k: int = 5


class SearchResultResponse(BaseModel):
    chunk: str
    score: float
    title: str
    source: str
    episode: str
    speaker: str | None = None
    timestamp_range: str | None = None


class SearchResponse(BaseModel):
    query: str
    found: bool
    results: list[SearchResultResponse]
