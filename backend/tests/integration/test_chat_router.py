from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.domain.entities.agent_result import AgentResult
from app.domain.entities.message import Message
from app.domain.interfaces.agent_harness import IAgentHarness
from app.infrastructure.api.app import create_app
from app.infrastructure.api.deps import get_agent_harness, get_message_repository, get_session_repository
from app.infrastructure.database.repositories.message_repo import SqlAlchemyMessageRepository
from app.infrastructure.database.repositories.session_repo import SqlAlchemySessionRepository

FAKE_ASSISTANT_RESPONSE = "This is a fake harness response."


class FakeAgentHarness(IAgentHarness):
    def run(self, history: list[Message], user_message: str) -> AgentResult:
        return AgentResult(text=FAKE_ASSISTANT_RESPONSE)


@pytest.fixture
def client(db_session) -> TestClient:
    app = create_app()
    app.dependency_overrides[get_session_repository] = lambda: SqlAlchemySessionRepository(db_session)
    app.dependency_overrides[get_message_repository] = lambda: SqlAlchemyMessageRepository(db_session)
    app.dependency_overrides[get_agent_harness] = lambda: FakeAgentHarness()
    return TestClient(app)


def test_send_message_returns_harness_response(client: TestClient):
    session = client.post("/api/sessions", json={"title": "chat test"}).json()

    response = client.post("/api/chat", json={"session_id": session["id"], "message": "hello"})

    assert response.status_code == 200
    body = response.json()
    assert body["session_id"] == session["id"]
    assert body["assistant_message"] == FAKE_ASSISTANT_RESPONSE


def test_send_message_to_missing_session_returns_404(client: TestClient):
    response = client.post("/api/chat", json={"session_id": str(uuid4()), "message": "hello"})

    assert response.status_code == 404


def test_sent_messages_are_persisted_and_ordered(client: TestClient):
    session = client.post("/api/sessions", json={"title": "history test"}).json()

    client.post("/api/chat", json={"session_id": session["id"], "message": "first"})
    client.post("/api/chat", json={"session_id": session["id"], "message": "second"})

    history = client.get(f"/api/sessions/{session['id']}").json()

    roles_and_content = [(m["role"], m["content"]) for m in history["messages"]]
    assert roles_and_content == [
        ("user", "first"),
        ("assistant", FAKE_ASSISTANT_RESPONSE),
        ("user", "second"),
        ("assistant", FAKE_ASSISTANT_RESPONSE),
    ]


def test_send_message_bumps_session_updated_at(client: TestClient):
    session = client.post("/api/sessions", json={"title": "touch test"}).json()

    client.post("/api/chat", json={"session_id": session["id"], "message": "hi"})

    refreshed = client.get(f"/api/sessions/{session['id']}").json()["session"]
    assert refreshed["updated_at"] > session["updated_at"]
