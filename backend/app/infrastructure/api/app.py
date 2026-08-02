import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import OperationalError

from app.core.config import get_settings
from app.core.logging import configure_logging
from app.core.runtime import SUBPROCESS_UNSUPPORTED_MESSAGE, event_loop_supports_subprocess
from app.domain.exceptions import HarnessUnavailableError, SessionNotFoundError
from app.infrastructure.api.v1.artifact_router import router as artifact_router
from app.infrastructure.api.v1.chat_router import router as chat_router
from app.infrastructure.api.v1.ingest_router import router as ingest_router
from app.infrastructure.api.v1.search_router import router as search_router
from app.infrastructure.api.v1.session_router import router as session_router

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Warns — loudly — if this process can't run the streaming chat path.

    Deliberately a CRITICAL log rather than a raised exception: the condition
    only breaks turns that actually reach the Claude Agent SDK, so aborting
    startup would also kill perfectly valid setups (the integration tests boot
    the app with a stubbed IAgentHarness and never spawn anything). The
    matching, truthful error for a real turn is raised in AgentSdkHarness,
    where the capability is genuinely needed.
    """
    if not event_loop_supports_subprocess():
        logger.critical(SUBPROCESS_UNSUPPORTED_MESSAGE)
    yield


def create_app() -> FastAPI:
    configure_logging()
    settings = get_settings()

    app = FastAPI(title=settings.app_name, lifespan=lifespan)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.exception_handler(OperationalError)
    def handle_db_connection_error(request: Request, exc: OperationalError) -> JSONResponse:
        return JSONResponse(
            status_code=503,
            content={"detail": "Database is currently unavailable. Please try again shortly."},
        )

    @app.exception_handler(SessionNotFoundError)
    def handle_session_not_found(request: Request, exc: SessionNotFoundError) -> JSONResponse:
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    @app.exception_handler(HarnessUnavailableError)
    def handle_harness_unavailable(request: Request, exc: HarnessUnavailableError) -> JSONResponse:
        return JSONResponse(status_code=502, content={"detail": str(exc)})

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    app.include_router(session_router, prefix="/api")
    app.include_router(chat_router, prefix="/api")
    app.include_router(artifact_router, prefix="/api")
    app.include_router(ingest_router, prefix="/api")
    app.include_router(search_router, prefix="/api")

    return app
