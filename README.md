# Lenny Growth Assistant

A conversational AI assistant that answers product/growth questions grounded in Lenny's Podcast transcripts (RAG), writes Ship30for30-style essays, and generates Markdown/HTML artifacts. The Claude Agent SDK is the harness (owns the agent loop and tool selection); this project adds three domain tools, durable Postgres-backed sessions, grounding enforcement, and structured artifact extraction on top of it.

See `CLAUDE.md` for the operational architecture summary, and `docs/ARCHITECTURE.md`/`docs/PRD.md` for full detail.

## Prerequisites

- Python 3.10+
- Node.js (required by the Claude Agent SDK, which wraps the Claude Code CLI as a subprocess) and the Claude Code CLI installed
- Docker (Postgres + pgvector)
- [Ollama](https://ollama.com), with `nomic-embed-text` pulled — embeddings are always local regardless of `LLM_PROVIDER` (see `docs/design.md`)
- An `ANTHROPIC_API_KEY` if running with `LLM_PROVIDER=anthropic`

## Setup

```bash
cd backend
python -m venv .venv
source .venv/Scripts/activate   # or .venv/bin/activate on macOS/Linux
pip install -r requirements.txt -r requirements-dev.txt

cp .env.example .env
# edit .env: set LLM_PROVIDER, ANTHROPIC_API_KEY (if anthropic), etc.

ollama pull nomic-embed-text
```

## Running the database

```bash
cd deployment
docker compose up -d
```

This starts a single `pgvector/pgvector:pg16` container with **two** databases, created automatically on first start via `deployment/init/`:

- `lenny_growth_assistant` — the development database the app reads/writes.
- `lenny_growth_assistant_test` — used only by the pytest suite (see below). Both have the `vector` extension enabled.

If you already had the container running before this second database existed, recreate the volume so the init scripts run again: `docker compose down -v && docker compose up -d` (this wipes local dev data — re-run migrations/ingestion afterward).

## Running migrations

```bash
cd backend
alembic upgrade head
```

## Running the backend

```bash
cd backend
uvicorn app.main:app --port 8000
```

> **Windows: do not add `--reload`.** It silently breaks streaming chat — every
> message comes back as "Response was interrupted". uvicorn runs reload workers
> on a `SelectorEventLoop`, which cannot spawn subprocesses on Windows, and the
> Claude Agent SDK runs the Claude Code CLI as a subprocess. The server logs a
> CRITICAL warning at startup if you hit this. On macOS and Linux `--reload` is
> safe (their `SelectorEventLoop` supports subprocesses via child watchers), so
> add it there if you want hot reload. Details in
> `docs/agent-transcripts/build-log.md`.

Stop the server with **Ctrl+C**, not by force-killing it or closing the
terminal. On Windows a force-killed `--reload` parent leaves its worker alive
holding the port, and Windows permits a *second* server to bind the same port
alongside it — requests then get split between the old and new process, so
`.env` changes (like switching `LLM_PROVIDER`) appear to apply only
intermittently. If chat behaves inconsistently after a restart, check for
strays with `netstat -ano | findstr :8000` — more than one PID means this
happened.

## Running the frontend

```bash
cd frontend
npm install
npm run dev
```

## Ingesting transcripts

```bash
python scripts/run_ingestion.py path/to/transcript.md
```

## Running tests

```bash
cd deployment && docker compose up -d   # both databases must be up
cd ../backend
pytest tests/
```

Tests **never touch development data**. Postgres-backed integration tests (`tests/integration/test_pgvector_store.py`) run against `TEST_DATABASE_URL` (`lenny_growth_assistant_test`), a separate database from `DATABASE_URL` in the same container. Each test runs inside a transaction that is rolled back afterward, so nothing a test writes is ever committed — there is no `DELETE`-based cleanup that could reach real rows.

`backend/tests/conftest.py` asserts at collection time that `TEST_DATABASE_URL` and `DATABASE_URL` don't resolve to the same database; if they do, the suite raises immediately instead of running. Tests that need real Postgres skip cleanly (rather than failing the whole suite) if the test database isn't reachable.

Most unit tests use an in-memory SQLite database and don't need Docker running at all, But keeping Docker running is prefered during testing.
