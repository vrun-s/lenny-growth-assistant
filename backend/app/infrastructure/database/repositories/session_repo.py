from uuid import UUID

from sqlalchemy.orm import Session as DbSession

from app.domain.entities.session import Session
from app.domain.interfaces.repositories import ISessionRepository
from app.infrastructure.database.orm_models import ChatSessionModel


def _to_entity(model: ChatSessionModel) -> Session:
    return Session(
        id=model.id,
        title=model.title,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


class SqlAlchemySessionRepository(ISessionRepository):
    def __init__(self, db: DbSession) -> None:
        self._db = db

    def create(self, session: Session) -> Session:
        model = ChatSessionModel(
            id=session.id,
            title=session.title,
            created_at=session.created_at,
            updated_at=session.updated_at,
        )
        self._db.add(model)
        self._db.commit()
        self._db.refresh(model)
        return _to_entity(model)

    def get(self, session_id: UUID) -> Session | None:
        model = self._db.get(ChatSessionModel, session_id)
        return _to_entity(model) if model else None

    def list(self) -> list[Session]:
        models = self._db.query(ChatSessionModel).order_by(ChatSessionModel.created_at.desc()).all()
        return [_to_entity(model) for model in models]

    def delete(self, session_id: UUID) -> bool:
        model = self._db.get(ChatSessionModel, session_id)
        if model is None:
            return False
        self._db.delete(model)
        self._db.commit()
        return True
