from datetime import datetime, timedelta, timezone
from uuid import uuid4

from app.domain.entities.message import Message, MessageRole
from app.domain.entities.session import Session
from app.infrastructure.database.repositories.message_repo import SqlAlchemyMessageRepository
from app.infrastructure.database.repositories.session_repo import SqlAlchemySessionRepository


def _make_session(db_session) -> Session:
    now = datetime.now(timezone.utc)
    return SqlAlchemySessionRepository(db_session).create(
        Session(id=uuid4(), title="Test session", created_at=now, updated_at=now)
    )


def _make_message(session_id, role: MessageRole, content: str, created_at: datetime) -> Message:
    return Message(id=uuid4(), session_id=session_id, role=role, content=content, created_at=created_at)


def test_create_and_list_by_session_round_trip(db_session):
    session = _make_session(db_session)
    repo = SqlAlchemyMessageRepository(db_session)
    now = datetime.now(timezone.utc)

    created = repo.create(_make_message(session.id, MessageRole.USER, "hello", now))

    messages = repo.list_by_session(session.id)
    assert len(messages) == 1
    assert messages[0].id == created.id
    assert messages[0].role == MessageRole.USER
    assert messages[0].content == "hello"


def test_list_by_session_orders_oldest_first(db_session):
    session = _make_session(db_session)
    repo = SqlAlchemyMessageRepository(db_session)
    now = datetime.now(timezone.utc)

    third = repo.create(_make_message(session.id, MessageRole.ASSISTANT, "third", now + timedelta(seconds=2)))
    first = repo.create(_make_message(session.id, MessageRole.USER, "first", now))
    second = repo.create(_make_message(session.id, MessageRole.ASSISTANT, "second", now + timedelta(seconds=1)))

    messages = repo.list_by_session(session.id)

    assert [m.id for m in messages] == [first.id, second.id, third.id]


def test_list_by_session_only_returns_messages_for_that_session(db_session):
    session_a = _make_session(db_session)
    session_b = _make_session(db_session)
    repo = SqlAlchemyMessageRepository(db_session)
    now = datetime.now(timezone.utc)

    repo.create(_make_message(session_a.id, MessageRole.USER, "for a", now))
    repo.create(_make_message(session_b.id, MessageRole.USER, "for b", now))

    messages = repo.list_by_session(session_a.id)

    assert len(messages) == 1
    assert messages[0].content == "for a"


def test_list_by_session_empty_when_no_messages(db_session):
    session = _make_session(db_session)
    repo = SqlAlchemyMessageRepository(db_session)

    assert repo.list_by_session(session.id) == []


def test_citations_round_trip(db_session):
    session = _make_session(db_session)
    repo = SqlAlchemyMessageRepository(db_session)
    now = datetime.now(timezone.utc)
    message = Message(
        id=uuid4(),
        session_id=session.id,
        role=MessageRole.ASSISTANT,
        content="grounded answer",
        created_at=now,
        citations=["Annie Duke — Decision Making", "Eli Schwartz — SEO in the Age of AI"],
    )

    repo.create(message)

    stored = repo.list_by_session(session.id)
    assert stored[0].citations == ["Annie Duke — Decision Making", "Eli Schwartz — SEO in the Age of AI"]


def test_citations_default_to_empty_list(db_session):
    session = _make_session(db_session)
    repo = SqlAlchemyMessageRepository(db_session)
    now = datetime.now(timezone.utc)

    repo.create(_make_message(session.id, MessageRole.USER, "hello", now))

    stored = repo.list_by_session(session.id)
    assert stored[0].citations == []
