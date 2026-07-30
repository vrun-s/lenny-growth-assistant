from uuid import uuid4

import pytest

from app.application.skills.artifact_skill import generate_artifact
from app.domain.entities.artifact import Artifact, ArtifactType
from app.domain.interfaces.repositories import IArtifactRepository


class FakeArtifactRepository(IArtifactRepository):
    def __init__(self) -> None:
        self.saved: list[Artifact] = []

    def create(self, artifact: Artifact) -> Artifact:
        self.saved.append(artifact)
        return artifact

    def get(self, artifact_id):
        return next((a for a in self.saved if a.id == artifact_id), None)


def test_persists_a_markdown_artifact():
    repo = FakeArtifactRepository()
    session_id = uuid4()

    artifact = generate_artifact(session_id, "markdown", "# Title", repo)

    assert artifact.type == ArtifactType.MARKDOWN
    assert artifact.session_id == session_id
    assert artifact.content == "# Title"
    assert repo.saved == [artifact]


def test_persists_an_html_artifact():
    repo = FakeArtifactRepository()

    artifact = generate_artifact(uuid4(), "html", "<p>hi</p>", repo)

    assert artifact.type == ArtifactType.HTML


def test_rejects_an_invalid_artifact_type():
    repo = FakeArtifactRepository()

    with pytest.raises(ValueError, match="Invalid artifact type"):
        generate_artifact(uuid4(), "pdf", "content", repo)

    assert repo.saved == []
