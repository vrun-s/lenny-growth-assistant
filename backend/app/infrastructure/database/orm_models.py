import uuid
from datetime import datetime, timezone
from enum import Enum

from sqlalchemy import Enum as SqlEnum
from sqlalchemy import ForeignKey, Text, Uuid
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from app.domain.entities.artifact import ArtifactType
from app.domain.entities.message import MessageRole


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _enum_column(enum_type: type[Enum], name: str) -> SqlEnum:
    """Store the enum's *values* (e.g. "markdown"), not its member names.

    SQLAlchemy defaults to persisting member names, which would write "MARKDOWN"
    and disagree with the schema documented in PRD §11.3.
    """
    return SqlEnum(enum_type, name=name, values_callable=lambda e: [m.value for m in e])


class Base(DeclarativeBase):
    pass


class ChatSessionModel(Base):
    __tablename__ = "chat_sessions"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(default=_utcnow, onupdate=_utcnow)

    messages: Mapped[list["MessageModel"]] = relationship(
        back_populates="session", cascade="all, delete-orphan", passive_deletes=True
    )
    artifacts: Mapped[list["ArtifactModel"]] = relationship(
        back_populates="session", cascade="all, delete-orphan", passive_deletes=True
    )


class ArtifactModel(Base):
    __tablename__ = "artifacts"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("chat_sessions.id", ondelete="CASCADE"), nullable=False
    )
    type: Mapped[ArtifactType] = mapped_column(
        _enum_column(ArtifactType, "artifacttype"), nullable=False
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(default=_utcnow)

    session: Mapped["ChatSessionModel"] = relationship(back_populates="artifacts")


class MessageModel(Base):
    __tablename__ = "messages"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("chat_sessions.id", ondelete="CASCADE"), nullable=False
    )
    role: Mapped[MessageRole] = mapped_column(
        _enum_column(MessageRole, "messagerole"), nullable=False
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    artifact_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("artifacts.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(default=_utcnow)

    session: Mapped["ChatSessionModel"] = relationship(back_populates="messages")
