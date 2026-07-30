from collections.abc import Iterator

from fastapi import Depends
from sqlalchemy.orm import Session as DbSession

from app.domain.interfaces.repositories import ISessionRepository
from app.infrastructure.database.connection import get_db_session
from app.infrastructure.database.repositories.session_repo import SqlAlchemySessionRepository


def get_db() -> Iterator[DbSession]:
    yield from get_db_session()


def get_session_repository(db: DbSession = Depends(get_db)) -> ISessionRepository:
    return SqlAlchemySessionRepository(db)
