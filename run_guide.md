# Run Guide

Step-by-step commands to get Lenny Growth Assistant running end-to-end, either against **Claude on Anthropic's API** (cloud) or **a local model via Ollama**. Both paths share the same database, ingestion, backend, and frontend — the only thing that changes is `LLM_PROVIDER` (and the model-specific env vars) in `backend/.env`.

For the architecture behind the provider toggle, see `CLAUDE.md` and `docs/design.md`. This file is just the commands.

---

## 0. Prerequisites

- **Python 3.10+**
- **Node.js** and the **Claude Code CLI** — the Claude Agent SDK wraps the Claude Code CLI as a subprocess, so both must be installed even though this is a Python backend. Verify with:
  ```bash
  node --version
  claude --version
  ```
- **Docker** (runs Postgres + pgvector)
- **[Ollama](https://ollama.com)** — required in **both** paths. Embeddings (`nomic-embed-text`) always run locally via Ollama regardless of which chat provider you pick (see `docs/design.md` § Embedding provider). It is not optional even if you only ever use `LLM_PROVIDER=anthropic`.
- An **Anthropic API key with an available credit balance** if you plan to use the cloud path (`LLM_PROVIDER=anthropic`). A key that authenticates but has zero credit will fail every request with `"Credit balance is too low"`.

---

## 1. One-time setup

```bash
cd backend
python -m venv .venv
source .venv/Scripts/activate   # Windows Git Bash; use .venv/bin/activate on macOS/Linux

pip install -r requirements.txt -r requirements-dev.txt

cp .env.example .env
```

Embeddings model (always required, both paths):

```bash
ollama pull nomic-embed-text
```

### Edit `backend/.env`

Open `backend/.env` and set the values for the path you want — see [Section 4](#4-choose-a-provider) below for the exact `LLM_PROVIDER` block for each path. Leave everything else (`DATABASE_URL`, `TEST_DATABASE_URL`, `HARNESS_TIMEOUT_SECONDS`) at its default unless you have a reason to change it.

---

## 2. Start the database

```bash
cd deployment
docker compose up -d
```

This starts one `pgvector/pgvector:pg16` container with two databases (created automatically on first start via `deployment/init/`):

- `lenny_growth_assistant` — the app's dev database
- `lenny_growth_assistant_test` — used only by the pytest suite

If the container already existed before the test database was added, recreate the volume: `docker compose down -v && docker compose up -d` (wipes local dev data — re-run migrations/ingestion after).

---

## 3. Run migrations

```bash
cd backend
alembic upgrade head
```

---

## 4. Choose a provider

Pick one block, paste it into `backend/.env` (replacing the existing `LLM_PROVIDER=...` lines), then continue to [Section 5](#5-ingest-at-least-one-transcript).

### Option A — Cloud (Anthropic)

```bash
LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=sk-ant-...        # must have an available credit balance
ANTHROPIC_MODEL=claude-sonnet-4-5   # or another Claude model, e.g. claude-haiku-4-5
```

No chat model needs to be pulled locally — only the embeddings model from Section 1.

**Free alternative to a paid key:** if you already have an authenticated Claude Code session on this machine (`~/.claude/.credentials.json` exists — check with `ls ~/.claude/.credentials.json`), you can test the tool-calling path without any `ANTHROPIC_API_KEY` at all: just leave `ANTHROPIC_API_KEY` unset/empty and don't export it in your shell either. `Settings` will fail its startup validation in that case (it requires the key when `LLM_PROVIDER=anthropic`) — this only applies if you're driving the SDK directly in a script rather than through the FastAPI app; see `docs/agent-transcripts/build-log.md`'s 2026-07-31 "Anthropic-path verification" entry for how this was done as a diagnostic.

### Option B — Local (Ollama)

```bash
LLM_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=qwen3:8b
```

Pull a chat-capable model (separate from the `nomic-embed-text` embeddings model):

```bash
ollama pull qwen3:8b
```

Then make sure Ollama is actually serving:

```bash
ollama serve   # if it isn't already running as a background service
```

**Known limitation:** per `docs/agent-transcripts/build-log.md` (Phase 6), `qwen3:8b` and `llama3.1:8b` do **not** reliably emit a structured `ToolUseBlock` through the full Claude Agent SDK/CLI path — plain conversation (no tools) works correctly, but tool-triggering questions may get answered from the model's own general knowledge instead of via `rag_query`, or the model may write a JSON-shaped tool call as plain text instead of a real tool call. This was independently confirmed as a local-model limitation, not a project bug, by re-running the same wiring against Anthropic (works reliably) — see the same file's "Anthropic-path verification" entry. If you hit this, try a model Ollama documents as tool-calling-capable (`qwen2.5`, `mistral-nemo`) — not yet verified in this repo, but recommended in the build log as the next thing to try.

---

## 5. Ingest at least one transcript

Both providers only answer from ingested transcripts (`rag_query` returns nothing otherwise, and the system prompt forbids answering from general knowledge). Grab a transcript from `github.com/ChatPRD/lennys-podcast-transcripts` or use your own Markdown file in the same format, then:

```bash
# from the repo root, with backend/.venv activated
python scripts/run_ingestion.py path/to/transcript.md
```

Repeat for as many episodes as you want available for retrieval.

---

## 6. Run the backend

```bash
cd backend
uvicorn app.main:app --port 8000
```

Leave this running. The API is now at `http://localhost:8000`.

---

## 7. Run the frontend

In a separate terminal:

```bash
cd frontend
npm install
npm run dev
```

Open the URL Vite prints (default `http://localhost:5173`) and chat through the UI.

---

## 8. Or test the API directly (no frontend)

Create a session, then send a message:

```bash
# 1. Create a session — capture the returned "id"
SESSION_ID=$(curl -s -X POST http://localhost:8000/api/sessions \
  -H "Content-Type: application/json" -d '{}' | python -c "import sys,json;print(json.load(sys.stdin)['id'])")

# 2. Send a chat message
curl -s -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d "{\"session_id\": \"$SESSION_ID\", \"message\": \"what makes a good decision maker?\"}"
```

A healthy response includes `assistant_message` grounded in transcript content and a non-empty `citations` array (assuming a relevant transcript was ingested). An empty `citations` array with a general-knowledge-sounding answer signals the tool wasn't called — see the known Ollama limitation above.

---

## 9. Switching providers later

Edit the `LLM_PROVIDER` block in `backend/.env` to the other option in [Section 4](#4-choose-a-provider), then restart `uvicorn` (Ctrl+C, re-run the Section 6 command). No migration or re-ingestion is needed — the corpus and sessions are provider-independent.

---

## 10. Running tests

```bash
cd deployment && docker compose up -d   # both databases must be up
cd ../backend
pytest tests/
```

Tests never touch dev data — Postgres-backed integration tests use `TEST_DATABASE_URL` (a separate database), each inside a rolled-back transaction. Most unit tests use in-memory SQLite and don't need Docker at all. Do not run the full suite while a real ingestion job is mid-flight (see `docs/agent-transcripts/build-log.md`'s "Real ingestion silently wiped..." entry) — `test_pgvector_store.py`'s fixture clears the `documents` table before/after each test in that file.

---

## Troubleshooting

| Symptom | Likely cause |
|---|---|
| App fails at startup with a missing `ANTHROPIC_API_KEY` error | `LLM_PROVIDER=anthropic` but the key isn't set in `backend/.env` — required, fails fast by design |
| Chat request fails with "Local model didn't respond — is Ollama running?" | Ollama isn't running, or `OLLAMA_BASE_URL` is wrong — check `ollama serve` and `OLLAMA_BASE_URL` |
| Chat request returns a generic AI error / `HarnessUnavailableError` on the Anthropic path | Check the backend logs for the underlying `ResultMessage` text — a common cause is an API key with a zero credit balance ("Credit balance is too low"), not a code bug |
| `rag_query` returns no citations / model answers from general knowledge | No transcripts ingested yet (Section 5), or — on the Ollama path — the local model's known tool-calling limitation (see Section 4, Option B) |
| `alembic upgrade head` fails with a connection error | Database isn't up — run Section 2 first |
| pytest integration tests fail/skip | `TEST_DATABASE_URL` unreachable — confirm `docker compose up -d` was run and both databases exist |
