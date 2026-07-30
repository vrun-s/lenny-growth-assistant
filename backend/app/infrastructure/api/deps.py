from fastapi import Depends
from sqlalchemy.orm import Session as DbSession

from app.domain.interfaces.repositories import ISessionRepository
from app.infrastructure.database.connection import get_db_session
from app.infrastructure.database.repositories.session_repo import SqlAlchemySessionRepository


def get_session_repository(db: DbSession = Depends(get_db_session)) -> ISessionRepository:
    return SqlAlchemySessionRepository(db)
