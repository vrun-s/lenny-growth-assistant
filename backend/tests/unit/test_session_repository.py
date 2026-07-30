from datetime import datetime, timezone
from uuid import uuid4

from app.domain.entities.session import Session
from app.infrastructure.database.repositories.session_repo import SqlAlchemySessionRepository


def _make_session(title: str = "Test session") -> Session:
    now = datetime.now(timezone.utc)
    return Session(id=uuid4(), title=title, created_at=now, updated_at=now)


def test_create_and_get_round_trip(db_session):
    repo = SqlAlchemySessionRepository(db_session)
    created = repo.create(_make_session("My session"))

    fetched = repo.get(created.id)

    assert fetched is not None
    assert fetched.id == created.id
    assert fetched.title == "My session"


def test_get_missing_session_returns_none(db_session):
    repo = SqlAlchemySessionRepository(db_session)

    assert repo.get(uuid4()) is None


def test_list_returns_all_sessions_newest_first(db_session):
    repo = SqlAlchemySessionRepository(db_session)
    first = repo.create(_make_session("first"))
    second = repo.create(_make_session("second"))

    sessions = repo.list()

    assert [s.id for s in sessions] == [second.id, first.id]


def test_delete_existing_session_returns_true(db_session):
    repo = SqlAlchemySessionRepository(db_session)
    created = repo.create(_make_session())

    deleted = repo.delete(created.id)

    assert deleted is True
    assert repo.get(created.id) is None


def test_delete_missing_session_returns_false(db_session):
    repo = SqlAlchemySessionRepository(db_session)

    assert repo.delete(uuid4()) is False


def test_touch_bumps_updated_at(db_session):
    repo = SqlAlchemySessionRepository(db_session)
    created = repo.create(_make_session())
    original_updated_at = created.updated_at

    repo.touch(created.id)

    assert repo.get(created.id).updated_at > original_updated_at


def test_touch_missing_session_is_a_no_op(db_session):
    repo = SqlAlchemySessionRepository(db_session)

    repo.touch(uuid4())  # must not raise


def test_delete_session_cascades_to_messages(db_session):
    from app.domain.entities.message import Message, MessageRole
    from app.infrastructure.database.repositories.message_repo import SqlAlchemyMessageRepository

    session_repo = SqlAlchemySessionRepository(db_session)
    message_repo = SqlAlchemyMessageRepository(db_session)

    session = session_repo.create(_make_session())
    message_repo.create(
        Message(
            id=uuid4(),
            session_id=session.id,
            role=MessageRole.USER,
            content="hello",
            created_at=datetime.now(timezone.utc),
        )
    )

    session_repo.delete(session.id)

    assert message_repo.list_by_session(session.id) == []
