"""Plain callable — no SDK import (per ARCHITECTURE.md §4.7).

Persistence + validation only — the Markdown/HTML content itself is composed
by the model as part of its tool call, not generated here. Validates the
declared type and persists {session_id, type, content} via IArtifactRepository.
"""

from datetime import datetime, timezone
from uuid import UUID, uuid4

from app.domain.entities.artifact import Artifact, ArtifactType
from app.domain.interfaces.repositories import IArtifactRepository


def generate_artifact(
    session_id: UUID,
    artifact_type: str,
    content: str,
    artifact_repo: IArtifactRepository,
) -> Artifact:
    try:
        resolved_type = ArtifactType(artifact_type)
    except ValueError:
        raise ValueError(
            f"Invalid artifact type '{artifact_type}'; must be 'markdown' or 'html'"
        ) from None

    artifact = Artifact(
        id=uuid4(),
        session_id=session_id,
        type=resolved_type,
        content=content,
        created_at=datetime.now(timezone.utc),
    )
    return artifact_repo.create(artifact)
