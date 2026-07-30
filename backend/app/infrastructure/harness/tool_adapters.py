"""Registers the application/skills/ callables as Claude Agent SDK tools.

Tool *registration* lives here; tool *logic* lives in application/skills/.
This is the documented exception in CLAUDE.md: infrastructure/harness/ may
import from application/skills/ (an inward dependency), and this is the only
place — besides agent_sdk_harness.py — that imports claude_agent_sdk.

Each tool handler catches its skill's exceptions and returns them as an
`is_error` tool_result (per PRD §7.1: "tool raises -> caught in
tool_adapters.py, returned to the loop as a tool_result error so the model
can recover") rather than letting them propagate and crash the harness loop.
"""

import json
import logging
from typing import Any
from uuid import UUID

from claude_agent_sdk import McpSdkServerConfig, create_sdk_mcp_server, tool

from app.application.skills.artifact_skill import generate_artifact
from app.application.skills.rag_skill import rag_query
from app.application.skills.ship30_skill import write_ship30_essay
from app.application.use_cases.retrieve_context import RetrieveContextUseCase
from app.domain.entities.artifact import Artifact
from app.domain.interfaces.repositories import IArtifactRepository

logger = logging.getLogger(__name__)

SERVER_NAME = "lenny_tools"
RAG_TOOL_NAME = "rag_query"
SHIP30_TOOL_NAME = "write_ship30_essay"
ARTIFACT_TOOL_NAME = "generate_artifact"

ALLOWED_TOOLS = [
    f"mcp__{SERVER_NAME}__{RAG_TOOL_NAME}",
    f"mcp__{SERVER_NAME}__{SHIP30_TOOL_NAME}",
    f"mcp__{SERVER_NAME}__{ARTIFACT_TOOL_NAME}",
]


class ToolRunResults:
    """Mutable, per-turn capture of tool side effects agent_sdk_harness.py
    needs after the loop finishes. Tool handlers only get to return
    JSON-able dicts to the model — this is the out-of-band channel that
    carries citations and any persisted Artifact back out into AgentResult.
    """

    def __init__(self) -> None:
        self.citations: list[str] = []
        self.artifact: Artifact | None = None

    def add_citations(self, citations: list[str]) -> None:
        for citation in citations:
            if citation not in self.citations:
                self.citations.append(citation)


def _text_result(payload: dict[str, Any]) -> dict[str, Any]:
    return {"content": [{"type": "text", "text": json.dumps(payload)}]}


def _error_result(exc: Exception) -> dict[str, Any]:
    return {"content": [{"type": "text", "text": f"Error: {exc}"}], "is_error": True}


async def handle_rag_query(
    args: dict[str, Any], *, retrieve_context: RetrieveContextUseCase, results: ToolRunResults
) -> dict[str, Any]:
    try:
        data = rag_query(args["question"], retrieve_context)
    except Exception as exc:  # noqa: BLE001 - must become a tool_result, not crash the loop
        logger.exception("rag_query tool failed")
        return _error_result(exc)
    results.add_citations(data["citations"])
    return _text_result(data)


async def handle_write_ship30_essay(
    args: dict[str, Any], *, retrieve_context: RetrieveContextUseCase, results: ToolRunResults
) -> dict[str, Any]:
    try:
        data = write_ship30_essay(args["topic"], retrieve_context)
    except Exception as exc:  # noqa: BLE001
        logger.exception("write_ship30_essay tool failed")
        return _error_result(exc)
    results.add_citations(data["citations"])
    return _text_result(data)


async def handle_generate_artifact(
    args: dict[str, Any],
    *,
    session_id: UUID,
    artifact_repo: IArtifactRepository,
    results: ToolRunResults,
) -> dict[str, Any]:
    try:
        artifact = generate_artifact(session_id, args["artifact_type"], args["content"], artifact_repo)
    except Exception as exc:  # noqa: BLE001
        logger.exception("generate_artifact tool failed")
        return _error_result(exc)
    results.artifact = artifact
    return _text_result({"artifact_id": str(artifact.id), "type": artifact.type.value})


def build_tool_server(
    *,
    retrieve_context: RetrieveContextUseCase,
    artifact_repo: IArtifactRepository,
    session_id: UUID,
    results: ToolRunResults,
) -> McpSdkServerConfig:
    """Builds one MCP server instance scoped to a single harness turn. Tool
    handlers close over this turn's session_id, use cases, and `results` box
    so the SDK-specific error handling and output capture stay in this file
    rather than leaking into application/skills/. The handle_* functions
    above hold the actual logic so they can be unit tested directly, without
    going through the SDK's tool dispatch.
    """

    @tool(
        RAG_TOOL_NAME,
        "Answer a product/growth question grounded in Lenny's Podcast transcripts. "
        "Use for any question answerable from the transcripts.",
        {"question": str},
    )
    async def _rag_query(args: dict[str, Any]) -> dict[str, Any]:
        return await handle_rag_query(args, retrieve_context=retrieve_context, results=results)

    @tool(
        SHIP30_TOOL_NAME,
        "Retrieve grounded material to write a Ship30for30-style essay on a topic.",
        {"topic": str},
    )
    async def _write_ship30_essay(args: dict[str, Any]) -> dict[str, Any]:
        return await handle_write_ship30_essay(args, retrieve_context=retrieve_context, results=results)

    @tool(
        ARTIFACT_TOOL_NAME,
        "Persist a generated standalone Markdown or HTML/CSS artifact and return its id. "
        "artifact_type must be 'markdown' or 'html'.",
        {"artifact_type": str, "content": str},
    )
    async def _generate_artifact(args: dict[str, Any]) -> dict[str, Any]:
        return await handle_generate_artifact(
            args, session_id=session_id, artifact_repo=artifact_repo, results=results
        )

    return create_sdk_mcp_server(
        name=SERVER_NAME,
        tools=[_rag_query, _write_ship30_essay, _generate_artifact],
    )
