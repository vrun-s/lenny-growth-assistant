from uuid import UUID

from sqlalchemy.orm import Session as DbSession

from app.domain.entities.artifact import Artifact
from app.domain.interfaces.repositories import IArtifactRepository
from app.infrastructure.database.orm_models import ArtifactModel


def _to_entity(model: ArtifactModel) -> Artifact:
    return Artifact(
        id=model.id,
        session_id=model.session_id,
        type=model.type,
        content=model.content,
        created_at=model.created_at,
    )


class SqlAlchemyArtifactRepository(IArtifactRepository):
    def __init__(self, db: DbSession) -> None:
        self._db = db

    def create(self, artifact: Artifact) -> Artifact:
        model = ArtifactModel(
            id=artifact.id,
            session_id=artifact.session_id,
            type=artifact.type,
            content=artifact.content,
            created_at=artifact.created_at,
        )
        self._db.add(model)
        self._db.commit()
        self._db.refresh(model)
        return _to_entity(model)

    def get(self, artifact_id: UUID) -> Artifact | None:
        model = self._db.get(ArtifactModel, artifact_id)
        return _to_entity(model) if model else None
