from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from app.domain.interfaces.repositories import IArtifactRepository
from app.infrastructure.api.deps import get_artifact_repository
from app.infrastructure.api.v1.schemas import ArtifactResponse

router = APIRouter(prefix="/artifacts", tags=["artifacts"])


@router.get("/{artifact_id}", response_model=ArtifactResponse)
def get_artifact(
    artifact_id: UUID,
    artifact_repo: IArtifactRepository = Depends(get_artifact_repository),
) -> ArtifactResponse:
    artifact = artifact_repo.get(artifact_id)
    if artifact is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Artifact not found")
    return ArtifactResponse.model_validate(artifact)
