from uuid import UUID

from sqlalchemy.orm import Session as DbSession

from app.domain.entities.message import Message
from app.domain.interfaces.repositories import IMessageRepository
from app.infrastructure.database.orm_models import MessageModel


def _to_entity(model: MessageModel) -> Message:
    return Message(
        id=model.id,
        session_id=model.session_id,
        role=model.role,
        content=model.content,
        created_at=model.created_at,
        artifact_id=model.artifact_id,
    )


class SqlAlchemyMessageRepository(IMessageRepository):
    def __init__(self, db: DbSession) -> None:
        self._db = db

    def create(self, message: Message) -> Message:
        model = MessageModel(
            id=message.id,
            session_id=message.session_id,
            role=message.role,
            content=message.content,
            artifact_id=message.artifact_id,
            created_at=message.created_at,
        )
        self._db.add(model)
        self._db.commit()
        self._db.refresh(model)
        return _to_entity(model)

    def list_by_session(self, session_id: UUID) -> list[Message]:
        models = (
            self._db.query(MessageModel)
            .filter(MessageModel.session_id == session_id)
            .order_by(MessageModel.created_at.asc())
            .all()
        )
        return [_to_entity(model) for model in models]
