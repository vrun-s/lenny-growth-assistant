from collections.abc import Iterator

import pytest
from sqlalchemy import create_engine, event, text
from sqlalchemy.engine import Connection, Engine, make_url
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session as DbSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import get_settings
from app.infrastructure.database.orm_models import Base
from app.infrastructure.vectorstore.pgvector_store import _VectorBase


@pytest.fixture(autouse=True)
def _default_test_settings(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    # LLM_PROVIDER=anthropic fails fast without a key (by design) — tests that
    # don't exercise the real harness still need create_app() to boot.
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test-not-a-real-key")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture
def db_session() -> Iterator[DbSession]:
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def _enable_sqlite_foreign_keys(dbapi_connection, _):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(engine)
    TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


def _assert_test_database_is_isolated_from_dev(database_url: str, test_database_url: str) -> None:
    """Hard safety check: tests must never be able to reach the development
    database. Raises rather than skips, so a misconfigured .env fails loudly
    instead of quietly running (or destructively wiping) the wrong database.
    """
    if database_url == test_database_url:
        raise RuntimeError(
            "TEST_DATABASE_URL is identical to DATABASE_URL. Refusing to run tests, "
            "which would delete development data. Set TEST_DATABASE_URL to a separate "
            "database (see backend/.env.example)."
        )

    dev_name = make_url(database_url).database
    test_name = make_url(test_database_url).database
    if dev_name == test_name:
        raise RuntimeError(
            f"DATABASE_URL and TEST_DATABASE_URL both resolve to database {dev_name!r}. "
            "Refusing to run tests, which would delete development data. Point "
            "TEST_DATABASE_URL at a separate database (see backend/.env.example)."
        )


@pytest.fixture(scope="session")
def pg_test_engine() -> Iterator[Engine]:
    """Session-scoped engine bound to TEST_DATABASE_URL. Creates the schema
    once (both `orm_models.Base` and pgvector's `_VectorBase`, matching the
    two DeclarativeBases the app actually uses) and skips dependent tests
    cleanly if the test database isn't reachable.
    """
    settings = get_settings()
    _assert_test_database_is_isolated_from_dev(settings.database_url, settings.test_database_url)

    engine = create_engine(settings.test_database_url, connect_args={"connect_timeout": 3})
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except OperationalError:
        engine.dispose()
        pytest.skip(
            "Postgres test database not reachable — start `docker compose up -d` "
            "(see backend/.env.example for TEST_DATABASE_URL)"
        )

    Base.metadata.create_all(engine)
    _VectorBase.metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture
def pg_connection(pg_test_engine: Engine) -> Iterator[Connection]:
    """A single open connection with a transaction that is rolled back after
    the test, giving Postgres-backed tests isolation without deleting rows —
    replaces the previous session.query(...).delete() cleanup, which wiped
    whatever data was in the table at the time (including, twice, real
    ingested development data when tests and dev pointed at the same DB).
    """
    connection = pg_test_engine.connect()
    transaction = connection.begin()
    try:
        yield connection
    finally:
        transaction.rollback()
        connection.close()


@pytest.fixture
def pg_session(pg_connection: Connection) -> Iterator[DbSession]:
    TestingSessionLocal = sessionmaker(bind=pg_connection, expire_on_commit=False)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
