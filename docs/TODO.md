# TODO — Lenny Growth Assistant

Checklist mirror of `workflow.md`. Two tracks run in parallel:

```
Track A (Core):  Phase 0 → 1 → 2 → 3 → 5 → 6 → 7 → 8 → 9
Track B (RAG):   Phase 0 → 4 ───────────────┘ (feeds into Phase 5)
```

Legend: ⚠ = named grading criterion, don't defer to Phase 9. 🔒 = decide now, expensive to reverse later.

---

## Phase 0 — Project Foundation

- [x] FastAPI boots
- [x] Config loads (`backend/app/core/config.py`)
- [x] Logging works (`backend/app/core/logging.py`)
- [x] `/health` endpoint responds
- [x] React boots (Vite)
- [x] Routing works (`/` and `/settings`)
- [x] API client exists (`frontend/src/core/api_client.ts`)
- [x] 🔒 Local embedding provider decided (e.g. `nomic-embed-text` via Ollama, or local `sentence-transformers`) and written into `docs/design.md`
- [x] `docker-compose.yml` brings up Postgres+pgvector (config verified; not smoke-tested — Docker Desktop daemon not running in this environment)

**Deliverable:** backend + frontend both start; embedding decision documented.
**Commit:** `chore: scaffold project foundation`

---

## Phase 1 — Database & Persistence *(Track A)*

- [ ] Domain entities: `Session`, `Message`, `Artifact`, `Document` (pure dataclasses, no SQLAlchemy/Pydantic inheritance)
- [ ] ORM models (`infrastructure/database/orm_models.py`)
- [ ] Repositories (`infrastructure/database/repositories/`) implementing `IRepository`
- [ ] Alembic migration
- [ ] `POST /sessions`
- [ ] `GET /sessions`
- [ ] `DELETE /sessions/{id}`
- [ ] ⚠ DB connection failure → API returns 503 with clear error body
- [ ] Unit tests: repository CRUD round-trips

**Deliverable:** can create and retrieve sessions.
**Commit:** `feat: implement conversation persistence`

---

## Phase 2 — Basic Chat *(Track A)*

- [ ] `POST /chat` returns a dummy response
- [ ] Conversation saved on each turn
- [ ] Chat window (frontend)
- [ ] Input (frontend)
- [ ] Message history renders (frontend)

**Deliverable:** can chat; messages persist across reload.
**Commit:** `feat: implement chat workflow`

---

## Phase 3 — Provider Layer *(Track A)*

- [ ] `BaseProvider` interface (domain port)
- [ ] `AnthropicProvider`
- [ ] `OpenAIProvider`
- [ ] `OllamaProvider`
- [ ] `LLM_PROVIDER=...` env var switches implementation
- [ ] ⚠ Missing API key → fail fast at startup, name the missing env var
- [ ] ⚠ Ollama unreachable/timeout → chat-visible error, configurable timeout (default 30s)
- [ ] Unit tests: mock each provider

**Deliverable:** one env var swaps providers; both failure modes demonstrable.
**Commit:** `feat: add configurable LLM providers`

---

## Phase 4 — Knowledge Base / RAG *(Track B — parallel with Phases 1–3)*

- [ ] Parser (`infrastructure/ingestion/parser.py`)
- [ ] Chunker (`infrastructure/ingestion/chunker.py`)
- [ ] Embedder (`infrastructure/ingestion/embedder.py`) using the Phase 0 local embedding model
- [ ] Loader (`infrastructure/ingestion/loader.py`) → pgvector
- [ ] Retriever (`infrastructure/vectorstore/retriever.py`)
- [ ] Standalone CLI: `scripts/run_ingestion.py` (zero business logic)
- [ ] ⚠ Retrieval with no relevant chunks → returns empty/flag so the RAG skill can decline (not guess)
- [ ] Unit tests: retrieval against a fixture set of transcript chunks

**Deliverable:** `retrieve(query)` returns relevant chunks, provable from a bare script before any chat UI exists. **Satisfies PRD Day 1 target.**
**Commit:** `feat: implement document ingestion and retrieval`

---

## Phase 5 — Skills *(Track A, needs Phase 3 + Phase 4)*

- [ ] RAG Skill: retriever → prompt template → provider → cited answer
- [ ] RAG Skill: wire in no-chunks-found decline behavior
- [ ] Ship30 Skill: prompt → Ship30 template → provider → ~1250-word essay
- [ ] Artifact Skill: prompt → generate HTML/Markdown → save artifact → return artifact ID
- [ ] ⚠ Each skill tested in isolation against PRD's named success criteria (grounded+cited RAG; Ship30 structure/length; valid single-fenced-block artifact)

**Deliverable:** each skill callable and correct on its own, independent of routing.
**Commit:** `feat: implement agent skills`

---

## Phase 6 — Router *(Track A)*

- [ ] Cloud providers (Anthropic/OpenAI): native tool-calling with the three tools (`rag_query`, `write_ship30_essay`, `generate_artifact`)
- [ ] Ollama: try native tool-calling first if model supports it
- [ ] ⚠ Malformed tool-call output → fallback prompted classifier (`RAG | SHIP30 | ARTIFACT | GENERAL`), parsed defensively, default to `RAG` on parse failure
- [ ] Unit tests: router fallback logic, including malformed-output path

**Deliverable:** the agent chooses the skill, not the user — provable on both Anthropic and Ollama.
**Commit:** `feat: implement agent routing`

---

## Phase 7 — Frontend *(Track A)*

- [ ] Sidebar
- [ ] Session switching
- [ ] Settings page
- [ ] New Chat / Delete Chat / switch session
- [ ] ⚠ DB failure banner in UI, consuming the Phase 1 503 response
- [ ] ⚠ In-flight messages never silently dropped on any named failure mode

**Deliverable:** full session UX works end to end.
**Commit:** `feat: implement chat interface`

---

## Phase 8 — Artifact Viewer *(Track A)*

- [ ] Detect artifact type (Markdown vs HTML) from tool-call structured output, not raw text parsing
- [ ] Markdown rendering via `react-markdown` + `rehype-sanitize`
- [ ] HTML/CSS rendering via sandboxed `<iframe srcDoc>` — never injected into parent DOM
- [ ] Viewer opens automatically when an artifact is produced

**Deliverable:** Markdown and HTML/CSS artifacts render side-by-side with chat.
**Commit:** `feat: add artifact viewer`

---

## Phase 9 — Polish, Testing, Docs

- [ ] Streaming (SSE) — if time allows; artifacts still render only once a message finishes
- [ ] Loading / typing indicators
- [ ] Markdown syntax highlighting
- [ ] Frontend smoke tests (Playwright): message renders; artifact triggers viewer
- [ ] Manual E2E pass: full run on Anthropic
- [ ] Manual E2E pass: full run on Ollama, including one deliberate error case
- [ ] README
- [ ] Confirm `docs/ARCHITECTURE.md` matches what was actually built
- [ ] Fill in `docs/design.md` (embedding decision + any other standing decisions)
- [ ] Demo video
- [ ] ⚠ `docs/agent-transcripts/` populated throughout the build (not reconstructed at the end)

**Deliverable:** demo-ready build with docs, tests, and a real failure log.
**Commit:** `docs: complete project documentation`

---

## Guardrails — do not build these

- [ ] ❌ No premature optimization
- [ ] ❌ No enterprise DI container (`container.py` stays removed — use FastAPI `Depends`)
- [ ] ❌ No event bus, mediator, or CQRS
- [ ] ❌ No dynamic skill registry / `BaseSkill` abstraction
- [ ] ❌ No ChromaDB or second vector store
- [ ] ❌ No Monaco Editor
- [ ] ❌ No chat renaming feature
