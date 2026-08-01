from datetime import UTC, datetime
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.domain.entities.artifact import Artifact, ArtifactType
from app.domain.interfaces.repositories import IArtifactRepository
from app.infrastructure.api.app import create_app
from app.infrastructure.api.deps import get_artifact_repository
from app.infrastructure.database.orm_models import ChatSessionModel
from app.infrastructure.database.repositories.artifact_repo import SqlAlchemyArtifactRepository


@pytest.fixture
def client(db_session) -> TestClient:
    app = create_app()
    app.dependency_overrides[get_artifact_repository] = lambda: SqlAlchemyArtifactRepository(db_session)
    return TestClient(app)


def _seed_session(db_session) -> ChatSessionModel:
    session = ChatSessionModel(id=uuid4(), title="artifact test session")
    db_session.add(session)
    db_session.commit()
    return session


def test_get_artifact_returns_200_with_correct_shape(client: TestClient, db_session):
    session = _seed_session(db_session)
    repo = SqlAlchemyArtifactRepository(db_session)
    artifact = repo.create(
        Artifact(
            id=uuid4(),
            session_id=session.id,
            type=ArtifactType.MARKDOWN,
            content="# Hello\n\nSome **bold** text.",
            created_at=datetime.now(UTC),
        )
    )

    response = client.get(f"/api/artifacts/{artifact.id}")

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == str(artifact.id)
    assert body["session_id"] == str(session.id)
    assert body["type"] == "markdown"
    assert body["content"] == "# Hello\n\nSome **bold** text."
    assert "created_at" in body


def test_get_artifact_returns_200_for_html_type(client: TestClient, db_session):
    session = _seed_session(db_session)
    repo = SqlAlchemyArtifactRepository(db_session)
    artifact = repo.create(
        Artifact(
            id=uuid4(),
            session_id=session.id,
            type=ArtifactType.HTML,
            content="<p>hi</p>",
            created_at=datetime.now(UTC),
        )
    )

    response = client.get(f"/api/artifacts/{artifact.id}")

    assert response.status_code == 200
    assert response.json()["type"] == "html"


def test_get_missing_artifact_returns_404(client: TestClient):
    response = client.get(f"/api/artifacts/{uuid4()}")

    assert response.status_code == 404


def test_get_artifact_with_malformed_id_is_not_a_500(client: TestClient):
    """Not a valid UUID at all — FastAPI's path-param validation should
    reject this as a 422 before it ever reaches the repository, not crash.
    """
    response = client.get("/api/artifacts/not-a-uuid")

    assert response.status_code == 422


def test_persisted_artifact_with_invalid_type_fails_at_the_response_boundary_not_silently(
    client: TestClient, db_session
):
    """artifact_skill.py's own unit tests (test_artifact_skill.py) already
    assert that generate_artifact() rejects an invalid type before
    persistence ever happens — so a malformed type can only reach this
    router via a fake/misbehaving repository, not through the real
    persistence path. This confirms that if it ever did, the response_model
    (ArtifactResponse.type: ArtifactType) boundary rejects the malformed
    data with a server error rather than silently serializing it — the
    validation guarantee survives up through the HTTP boundary rather than
    being a skill-layer-only guarantee.
    """

    class InvalidTypeArtifactRepository(IArtifactRepository):
        def create(self, artifact: Artifact) -> Artifact:
            raise NotImplementedError

        def get(self, artifact_id):
            return Artifact(
                id=artifact_id,
                session_id=uuid4(),
                type="pdf",  # type: ignore[arg-type]  — deliberately invalid
                content="whatever",
                created_at=datetime.now(UTC),
            )

    app = create_app()
    app.dependency_overrides[get_artifact_repository] = lambda: InvalidTypeArtifactRepository()
    broken_client = TestClient(app, raise_server_exceptions=False)

    response = broken_client.get(f"/api/artifacts/{uuid4()}")

    assert response.status_code == 500
