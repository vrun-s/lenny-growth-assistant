"""Runtime environment checks — pure bootstrapping, stdlib only.

Exists because of one Windows-specific incompatibility between uvicorn and the
Claude Agent SDK; see `SUBPROCESS_UNSUPPORTED_MESSAGE` below for the full story.
"""

import asyncio
import sys

# Shown both at startup (as a CRITICAL log) and as the chat-visible error if a
# turn is actually attempted, so the two can never drift apart. Phrased as an
# instruction rather than a diagnosis — the evaluator needs the fix, not the
# asyncio internals.
SUBPROCESS_UNSUPPORTED_MESSAGE = (
    "Server started with --reload on Windows, which breaks streaming chat. "
    "uvicorn runs reload workers on a SelectorEventLoop, which cannot spawn "
    "subprocesses on Windows, and the Claude Agent SDK runs the Claude Code "
    "CLI as a subprocess. Restart without --reload: "
    "`uvicorn app.main:app --port 8000`."
)


def event_loop_supports_subprocess() -> bool:
    """Whether the *currently running* event loop can spawn subprocesses.

    Only Windows can answer False. There, `asyncio.SelectorEventLoop` raises
    NotImplementedError from `_make_subprocess_transport`, while
    `ProactorEventLoop` (the interpreter default since 3.8) works. uvicorn
    deliberately picks Selector whenever it runs the app in a subprocess —
    i.e. `--reload` or `--workers N` — see `uvicorn/loops/asyncio.py`:

        if sys.platform == "win32" and not use_subprocess:
            return asyncio.ProactorEventLoop
        return asyncio.SelectorEventLoop

    On Unix, SelectorEventLoop implements subprocess support via child
    watchers, so `--reload` is harmless there and this always returns True.

    Note this is about the loop *serving the request*. `AgentSdkHarness.run()`
    (the non-streaming path) calls `asyncio.run()`, which builds a fresh loop
    from the default policy and is therefore unaffected; only `run_stream()`,
    which executes inside uvicorn's own loop, inherits the broken one.
    """
    if sys.platform != "win32":
        return True

    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        # Called outside a running loop — nothing to judge yet, and the
        # non-streaming path builds its own loop regardless.
        return True

    return isinstance(loop, asyncio.ProactorEventLoop)
