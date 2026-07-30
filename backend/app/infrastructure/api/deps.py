from fastapi import Depends
from sqlalchemy.orm import Session as DbSession

from app.domain.interfaces.agent_harness import IAgentHarness
from app.domain.interfaces.repositories import IMessageRepository, ISessionRepository
from app.infrastructure.database.connection import get_db_session
from app.infrastructure.database.repositories.message_repo import SqlAlchemyMessageRepository
from app.infrastructure.database.repositories.session_repo import SqlAlchemySessionRepository
from app.infrastructure.harness.agent_sdk_harness import AgentSdkHarness


def get_session_repository(db: DbSession = Depends(get_db_session)) -> ISessionRepository:
    return SqlAlchemySessionRepository(db)


def get_message_repository(db: DbSession = Depends(get_db_session)) -> IMessageRepository:
    return SqlAlchemyMessageRepository(db)


def get_agent_harness() -> IAgentHarness:
    return AgentSdkHarness()
