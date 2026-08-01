from datetime import datetime, timezone
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

from app.domain.entities.agent_result import AgentResult
from app.domain.entities.artifact import Artifact, ArtifactType
from app.domain.entities.message import Message
from app.domain.entities.stream_chunk import StreamChunk
from app.domain.interfaces.agent_harness import IAgentHarness
from app.domain.interfaces.repositories import IArtifactRepository
from app.infrastructure.api.app import create_app
from app.infrastructure.api.deps import get_agent_harness, get_message_repository, get_session_repository
from app.infrastructure.database.repositories.artifact_repo import SqlAlchemyArtifactRepository
from app.infrastructure.database.repositories.message_repo import SqlAlchemyMessageRepository
from app.infrastructure.database.repositories.session_repo import SqlAlchemySessionRepository

FAKE_ASSISTANT_RESPONSE = "This is a fake harness response."


class FakeAgentHarness(IAgentHarness):
    def run(self, history: list[Message], user_message: str, session_id: UUID) -> AgentResult:
        return AgentResult(text=FAKE_ASSISTANT_RESPONSE)

    async def run_stream(self, history: list[Message], user_message: str, session_id: UUID):
        yield StreamChunk(kind="final", result=self.run(history, user_message, session_id))


class FakeAgentHarnessWithArtifact(IAgentHarness):
    def __init__(self, artifact_repo: IArtifactRepository) -> None:
        self._artifact_repo = artifact_repo

    def run(self, history: list[Message], user_message: str, session_id: UUID) -> AgentResult:
        artifact = self._artifact_repo.create(
            Artifact(
                id=uuid4(),
                session_id=session_id,
                type=ArtifactType.MARKDOWN,
                content="# Generated",
                created_at=datetime.now(timezone.utc),
            )
        )
        return AgentResult(text="Here's your artifact.", citations=["Episode 1 — Lenny"], artifact=artifact)

    async def run_stream(self, history: list[Message], user_message: str, session_id: UUID):
        yield StreamChunk(kind="final", result=self.run(history, user_message, session_id))


class FakeStreamingAgentHarness(IAgentHarness):
    """Scripted multi-chunk sequence — text deltas, a tool-call-in-progress
    chunk, and a final chunk — for exercising the SSE route's framing and
    the use case's persistence-on-final behavior together, end to end.
    """

    def run(self, history: list[Message], user_message: str, session_id: UUID) -> AgentResult:
        raise NotImplementedError

    async def run_stream(self, history: list[Message], user_message: str, session_id: UUID):
        yield StreamChunk(kind="text", text="Hello")
        yield StreamChunk(kind="tool_call", tool_name="rag_query")
        yield StreamChunk(kind="text", text=" world")
        yield StreamChunk(kind="final", result=AgentResult(text="Hello world", citations=["Ep 1 — Lenny"]))


def _parse_sse(body: str) -> list[dict]:
    import json

    events = []
    for line in body.splitlines():
        if line.startswith("data: "):
            events.append(json.loads(line[len("data: ") :]))
    return events


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


def test_send_message_surfaces_citations_and_artifact_id(client: TestClient, db_session):
    client.app.dependency_overrides[get_agent_harness] = lambda: FakeAgentHarnessWithArtifact(
        SqlAlchemyArtifactRepository(db_session)
    )
    session = client.post("/api/sessions", json={"title": "artifact test"}).json()

    response = client.post("/api/chat", json={"session_id": session["id"], "message": "make an artifact"})

    body = response.json()
    assert body["citations"] == ["Episode 1 — Lenny"]
    assert body["artifact_id"] is not None

    history = client.get(f"/api/sessions/{session['id']}").json()
    assistant_message = next(m for m in history["messages"] if m["role"] == "assistant")
    assert assistant_message["artifact_id"] == body["artifact_id"]
    # Citations must survive a page refresh, not just live on the one-shot
    # ChatResponse — see docs/agent-transcripts/build-log.md's Step 0 finding.
    assert assistant_message["citations"] == ["Episode 1 — Lenny"]


def test_first_exchange_auto_names_the_session(client: TestClient):
    session = client.post("/api/sessions", json={"title": "New chat"}).json()

    client.post("/api/chat", json={"session_id": session["id"], "message": "hello"})

    refreshed = client.get(f"/api/sessions/{session['id']}").json()["session"]
    # FakeAgentHarness.run() returns the same fixed text regardless of the
    # prompt, so it also becomes the auto-generated title here — what
    # matters is that it's no longer the "New chat" placeholder, proving
    # AutoNameSessionUseCase actually ran (via the BackgroundTasks wiring in
    # chat_router.py) rather than just being reachable in isolation.
    assert refreshed["title"] == FAKE_ASSISTANT_RESPONSE


def test_second_exchange_does_not_rename_again(client: TestClient):
    session = client.post("/api/sessions", json={"title": "New chat"}).json()

    client.post("/api/chat", json={"session_id": session["id"], "message": "hello"})
    renamed_title = client.get(f"/api/sessions/{session['id']}").json()["session"]["title"]
    client.patch(f"/api/sessions/{session['id']}", json={"title": "My manual title"})

    client.post("/api/chat", json={"session_id": session["id"], "message": "second message"})

    refreshed = client.get(f"/api/sessions/{session['id']}").json()["session"]
    assert renamed_title == FAKE_ASSISTANT_RESPONSE
    assert refreshed["title"] == "My manual title"


def test_stream_to_missing_session_returns_404(client: TestClient):
    response = client.post("/api/chat/stream", json={"session_id": str(uuid4()), "message": "hello"})

    assert response.status_code == 404


def test_stream_returns_sse_frames_in_order_and_persists_final_message(client: TestClient):
    client.app.dependency_overrides[get_agent_harness] = lambda: FakeStreamingAgentHarness()
    session = client.post("/api/sessions", json={"title": "stream test"}).json()

    response = client.post("/api/chat/stream", json={"session_id": session["id"], "message": "hi"})

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")

    events = _parse_sse(response.text)
    assert [e["kind"] for e in events] == ["text", "tool_call", "text", "final"]
    assert events[0]["text"] == "Hello"
    assert events[1]["tool_name"] == "rag_query"
    assert events[2]["text"] == " world"
    assert events[3]["assistant_message"] == "Hello world"
    assert events[3]["citations"] == ["Ep 1 — Lenny"]

    history = client.get(f"/api/sessions/{session['id']}").json()
    roles_and_content = [(m["role"], m["content"]) for m in history["messages"]]
    assert roles_and_content == [("user", "hi"), ("assistant", "Hello world")]
    assistant_message = next(m for m in history["messages"] if m["role"] == "assistant")
    assert assistant_message["citations"] == ["Ep 1 — Lenny"]
