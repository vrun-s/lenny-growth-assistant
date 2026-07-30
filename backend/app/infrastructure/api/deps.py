from fastapi import Depends
from sqlalchemy.orm import Session as DbSession

from app.application.use_cases.retrieve_context import RetrieveContextUseCase
from app.domain.interfaces.agent_harness import IAgentHarness
from app.domain.interfaces.repositories import IArtifactRepository, IMessageRepository, ISessionRepository
from app.domain.interfaces.vectorstore import IVectorStore
from app.infrastructure.database.connection import get_db_session
from app.infrastructure.database.repositories.artifact_repo import SqlAlchemyArtifactRepository
from app.infrastructure.database.repositories.message_repo import SqlAlchemyMessageRepository
from app.infrastructure.database.repositories.session_repo import SqlAlchemySessionRepository
from app.infrastructure.harness.agent_sdk_harness import AgentSdkHarness
from app.infrastructure.vectorstore.pgvector_store import PgVectorStore


def get_session_repository(db: DbSession = Depends(get_db_session)) -> ISessionRepository:
    return SqlAlchemySessionRepository(db)


def get_message_repository(db: DbSession = Depends(get_db_session)) -> IMessageRepository:
    return SqlAlchemyMessageRepository(db)


def get_artifact_repository(db: DbSession = Depends(get_db_session)) -> IArtifactRepository:
    return SqlAlchemyArtifactRepository(db)


def get_vector_store() -> IVectorStore:
    return PgVectorStore()


def get_retrieve_context_use_case(
    vectorstore: IVectorStore = Depends(get_vector_store),
) -> RetrieveContextUseCase:
    return RetrieveContextUseCase(vectorstore)


def get_agent_harness(
    retrieve_context: RetrieveContextUseCase = Depends(get_retrieve_context_use_case),
    artifact_repo: IArtifactRepository = Depends(get_artifact_repository),
) -> IAgentHarness:
    return AgentSdkHarness(retrieve_context, artifact_repo)
