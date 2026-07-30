from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError

from app.domain.interfaces.repositories import ISessionRepository
from app.infrastructure.api.app import create_app
from app.infrastructure.api.deps import get_session_repository
from app.infrastructure.database.repositories.session_repo import SqlAlchemySessionRepository


@pytest.fixture
def client(db_session) -> TestClient:
    app = create_app()
    app.dependency_overrides[get_session_repository] = lambda: SqlAlchemySessionRepository(db_session)
    return TestClient(app)


def test_create_session_returns_201(client: TestClient):
    response = client.post("/api/sessions", json={"title": "My session"})

    assert response.status_code == 201
    body = response.json()
    assert body["title"] == "My session"
    assert "id" in body


def test_create_session_without_title_uses_default(client: TestClient):
    response = client.post("/api/sessions", json={})

    assert response.status_code == 201
    assert response.json()["title"] == "New chat"


def test_list_sessions_returns_created_sessions(client: TestClient):
    client.post("/api/sessions", json={"title": "first"})
    client.post("/api/sessions", json={"title": "second"})

    response = client.get("/api/sessions")

    assert response.status_code == 200
    titles = [s["title"] for s in response.json()]
    assert titles == ["second", "first"]


def test_delete_session_returns_204(client: TestClient):
    created = client.post("/api/sessions", json={"title": "to delete"}).json()

    response = client.delete(f"/api/sessions/{created['id']}")

    assert response.status_code == 204
    assert client.get("/api/sessions").json() == []


def test_delete_missing_session_returns_404(client: TestClient):
    response = client.delete(f"/api/sessions/{uuid4()}")

    assert response.status_code == 404


def test_get_session_returns_session_and_empty_messages(client: TestClient):
    created = client.post("/api/sessions", json={"title": "with history"}).json()

    response = client.get(f"/api/sessions/{created['id']}")

    assert response.status_code == 200
    body = response.json()
    assert body["session"]["id"] == created["id"]
    assert body["messages"] == []


def test_get_missing_session_returns_404(client: TestClient):
    response = client.get(f"/api/sessions/{uuid4()}")

    assert response.status_code == 404


def test_db_connection_failure_returns_503():
    class BrokenSessionRepository(ISessionRepository):
        def create(self, session):
            raise OperationalError("statement", {}, Exception("connection refused"))

        def get(self, session_id):
            raise OperationalError("statement", {}, Exception("connection refused"))

        def list(self):
            raise OperationalError("statement", {}, Exception("connection refused"))

        def delete(self, session_id):
            raise OperationalError("statement", {}, Exception("connection refused"))

        def touch(self, session_id):
            raise OperationalError("statement", {}, Exception("connection refused"))

    app = create_app()
    app.dependency_overrides[get_session_repository] = lambda: BrokenSessionRepository()
    client = TestClient(app, raise_server_exceptions=False)

    response = client.get("/api/sessions")

    assert response.status_code == 503
