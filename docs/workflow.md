# Workflow Guide — Lenny Growth Assistant

**Timeline:** 3 days (due Aug 2, 2026 EOD)
**Status:** Phases 0–2 complete. Phase 3 complete. Phase 4A complete and verified against a live Postgres+Ollama pair (migrations applied, real corpus ingested, pgvector integration tests green). Phase 4B complete: real skill bodies, `tool_adapters.py`, harness extended to register tools. Most of Phase 6 (tool registration + Ollama verification) was pulled forward and done alongside 4B — Anthropic-side tool-choice verification is the one item still open, blocked on an API key. Phase 5's checklist is satisfied by the same 4B work.
**Architecture note (2026-07-30):** Phase 3 and Phase 6 below were rewritten after an architecture correction — the project builds on the Claude Agent SDK as its harness rather than a hand-written provider hierarchy + router. Nothing in completed Phases 0–2 is affected; this only changes work that hadn't started yet. See `docs/ARCHITECTURE.md` §0 and §5–§6, and `docs/design.md`, for the full rationale.
**Purpose of this doc:** the single phase plan and checklist for this build — a practical, checkable build order that protects the PRD's Day 1 goal, bakes in the named grading criteria (error handling, testing, routing) as you go instead of at the end, and matches `ARCHITECTURE.md`'s layering. Check items off as you go — don't skip to Phase 9 items early, and don't defer them either.

---

## How to use this file

- Work top to bottom within a phase. Phases can overlap across the two tracks below (Core Track and Parallel RAG Track) — everything else is sequential.
- Each phase ends with a **Deliverable** (what "done" looks like) and a **Commit** message to use.
- Anything marked **⚠ Grading criterion** is explicitly called out in the PRD — do not defer it to Phase 9.
- Anything marked **Decide now** is a decision that's expensive to reverse later — settle it before writing code in that phase.

---

## Track overview

Two tracks run in parallel to protect the PRD's Day 1 goal ("answer a question grounded in transcripts, from the CLI or a bare API endpoint"):

```
Track A (Core):     Phase 0 → Phase 1 → Phase 2 → Phase 3 → Phase 5(skills) → Phase 6 → Phase 7 → Phase 8 → Phase 9
Track B (RAG):       Phase 0 → Phase 4 (ingestion + retrieval, standalone CLI) ─────────┘
```

Track B does not depend on `Session`/`Message`/`Artifact` tables — the `Documents` table and the parser → chunker → embedder → pgvector → retriever pipeline are independent. Build and prove `retrieve(query)` works from a bare script **before** the chat endpoint exists. This is the single biggest change from a naive "do everything in numeric order" plan.

**Sequencing note (from PRD §5):** once Phase 3's harness is up, test it against **Ollama before Anthropic**. The cloud path is low-risk; the local path is mandatory and the likeliest source of a surprise. Finding an incompatibility on Day 2 morning is recoverable — finding it on Day 3 evening is not.

---

## Implementation Scope

Only implement the milestone explicitly requested.

Do not:
- implement future milestones
- refactor unrelated files
- introduce new abstractions
- change the architecture unless asked

If a requested change affects another milestone, explain the tradeoff before proceeding.

## Phase 0 — Project Foundation

**Goal:** Everything runs.

### Backend
- [x] FastAPI boots
- [x] Config loads (`backend/app/core/config.py`, Pydantic settings)
- [x] Logging works (`backend/app/core/logging.py`)
- [x] `/health` endpoint responds

### Frontend
- [x] React boots (Vite)
- [x] Routing works (`/` and `/settings`)
- [x] API client exists (`frontend/src/core/api_client.ts`)

### 🔒 Decide now
- [x] **Embedding provider** — this must be decided in Phase 0, not Phase 4. §7.1's offline requirement (`LLM_PROVIDER=ollama`, no internet after initial pull) breaks silently if embeddings are generated via a cloud API while chat runs locally. Pick a **local embedding model** (e.g. `nomic-embed-text` via Ollama, or a local `sentence-transformers` model) so the same embedding path works regardless of `LLM_PROVIDER`. Write the decision into `docs/design.md`.
- [x] Confirm `docker-compose.yml` brings up Postgres+pgvector so Track B isn't blocked waiting on Phase 1's ORM work. *(Verified against a live container once Docker Desktop was started — see `agent-transcripts/build-log.md`.)*

**Deliverable:** `backend/` and `frontend/` both start successfully; embedding provider decision is written down.

**Commit:** `chore: scaffold project foundation`

---

## Phase 1 — Database & Persistence *(Track A)*

**Goal:** Store conversations.

- [x] Implement domain entities: `Session`, `Message`, `Artifact`, `Document` (pure dataclasses in `domain/entities/` — no SQLAlchemy/Pydantic inheritance, per ARCHITECTURE.md §4.1)
- [x] Create ORM models (`infrastructure/database/orm_models.py`)
- [x] Create repositories (`infrastructure/database/repositories/`) implementing the `IRepository` port
- [x] Alembic migration
- [x] API: `POST /sessions`, `GET /sessions`, `DELETE /sessions/{id}`

### ⚠ Grading criterion — start now, don't defer
- [x] **DB connection failure → 503.** Wire this in now while you're already touching the connection/repository layer, not as a Phase 9 add-on. API returns 503 with a clear error body on DB failure; note in `docs/design.md` that the frontend will show a banner (built in Phase 7) rather than a blank chat.

### Testing (write alongside, not later)
- [x] `tests/unit/` — repository CRUD round-trips against a test DB or fixtures.

**Deliverable:** Can create and retrieve sessions.

**Commit:** `feat: implement conversation persistence`

---

## Phase 2 — Basic Chat *(Track A)*

**Goal:** Prove the end-to-end flow. Forget AI for now.

```
User → POST /chat → Dummy response → Save conversation → Return response
```

### Backend
- [x] `MessageRepository` implementing `IMessageRepository` (`create`, `list_by_session` ordered oldest-first)
- [x] `SendMessageUseCase` (ports only — verifies session via `ISessionRepository`, persists user + dummy assistant message, bumps `updated_at`, raises `SessionNotFoundError` → 404)
- [x] `POST /api/chat` — `{session_id, message}` → `{session_id, assistant_message}`; 404 for a nonexistent session
- [x] `GET /api/sessions/{id}` — `{session, messages}`, messages oldest-first

### Frontend
- [x] Chat window
- [x] Input
- [x] Message history renders

**Deliverable:** You can chat. Messages persist. Reload the page — conversation still exists. *(Verified end-to-end against real Postgres — see `agent-transcripts/build-log.md`.)*

**Commit:** `feat: implement chat workflow`

**Note for Phase 3:** `SendMessageUseCase` currently returns a dummy assistant message. Phase 3 replaces that dummy call with `IAgentHarness.run(...)` — the persistence and 404 handling built here don't change.

---

## Phase 3 — Harness Layer *(Track A)*

**Goal:** Replace the dummy response with a real model, via a harness — not a hand-rolled provider hierarchy.

There is **no `BaseProvider`, no `AnthropicProvider`/`OpenAIProvider`/`OllamaProvider`, and no OpenAI support.** The Claude Agent SDK owns the agent loop; this phase wires it in behind one port. See `docs/ARCHITECTURE.md` §0 for the harness/orchestration distinction this phase depends on.

- [x] `IAgentHarness` port in `domain/interfaces/agent_harness.py` — `run(history, message) -> AgentResult`
- [x] `AgentResult` domain entity (`text`, `citations`, optional `artifact`) in `domain/entities/agent_result.py`
- [x] `agent_sdk_harness.py` in `infrastructure/harness/` — initializes the Claude Agent SDK, resolves `base_url`/model from config, runs a turn with **no tools yet** (tools come in Phase 6, after Phase 5 skills exist)
- [x] `core/config.py` resolves `LLM_PROVIDER` into a base URL + model name, not a class:
  - `anthropic` → Anthropic default base URL, `claude-sonnet-*`, requires `ANTHROPIC_API_KEY`
  - `ollama` → `http://localhost:11434`, a locally-pulled model, dummy API key (required by the client, ignored by Ollama)
- [x] `SendMessageUseCase` calls `IAgentHarness.run(...)` in place of the Phase 2 dummy response
- [x] Confirm the Node.js / Claude Code CLI runtime prerequisite for the Python Agent SDK is met locally — `claude` CLI 2.1.220 present and used by the SDK's subprocess transport; still owed a README write-up.
- [x] `rag_skill.py`/`ship30_skill.py`/`artifact_skill.py` — real bodies implemented in Phase 4B (see below).

### ⚠ Grading criterion — build here, not in Phase 9
- [x] **Missing `ANTHROPIC_API_KEY` when `LLM_PROVIDER=anthropic` → fail fast at startup**, naming the missing env var. Do this in config validation, not mid-conversation.
- [x] **Ollama unreachable / request timeout** → chat-visible error ("Local model didn't respond — is Ollama running?"), configurable timeout (default 30s). This is harness-layer code — write it now while you're inside `agent_sdk_harness.py`.

### Test Ollama now, not later
- [x] Run this harness against a local Ollama model. Plain (toolless) conversation confirmed working after three config fixes found in the process (`tools=[]`, `permission_mode="bypassPermissions"`, thinking disabled for Ollama — see `docs/design.md`/build-log). Tool-calling reliability specifically (once tools existed, Phase 4B/6) turned out to be a real per-model limitation with the locally-pulled `qwen3:8b` — logged, not silently routed around; see build-log's "Ollama tool-calling verification" entry.

### Testing (write alongside)
- [x] Mock `IAgentHarness` in `tests/unit/` for `SendMessageUseCase` tests — no network, no SDK.

**Deliverable:** Changing `LLM_PROVIDER` changes which model answers, with no code change; failure modes above are demonstrable (kill Ollama, unset the API key); confirmed working against a real local model, not just Anthropic.

**Commit:** `feat: add agent harness with cloud/local toggle`

---

## Phase 4 — Knowledge Base (RAG) *(Track B — run in parallel with Phases 1–3)*

**Goal:** Grounded retrieval, no LLM yet. This is the PRD's actual Day 1 deliverable — start it early, don't wait for persistence to finish.

```
Markdown transcripts → Parser → Chunker → Embeddings → pgvector → Retriever
```

- [x] Parser (`infrastructure/ingestion/parser.py`)
- [x] Chunker (`infrastructure/ingestion/chunker.py`)
- [ ] ~~Embedder (`infrastructure/ingestion/embedder.py`)~~ — intentionally left as a stub. Embedding lives solely in `infrastructure/vectorstore/embeddings.py` (per `design.md`'s existing "vectorstore/embeddings.py calls Ollama's /api/embeddings" decision); `IVectorStore.add_documents()` embeds internally, so ingestion never needs its own embedding call, and a second one would either duplicate the Ollama call or require a forbidden ingestion→vectorstore cross-import. Documented in `design.md`.
- [x] Loader (`infrastructure/ingestion/loader.py`) — thin parser+chunker orchestration; does not call pgvector directly (would be a forbidden cross-import), the composition layer (API router / CLI script) wires its output to `IngestDocumentsUseCase`
- [x] Embeddings (`infrastructure/vectorstore/embeddings.py`) — `OllamaEmbedder`, always local regardless of `LLM_PROVIDER`
- [x] Retriever (`infrastructure/vectorstore/retriever.py`) — pure ranking/citation-shaping, no DB/HTTP
- [x] pgvector store (`infrastructure/vectorstore/pgvector_store.py`) — owns its own engine + `documents` table model, independent of `infrastructure/database/`
- [x] Standalone CLI entrypoint: `scripts/run_ingestion.py` (zero business logic — just calls into `infrastructure/ingestion/`, per ARCHITECTURE.md §5)
- [x] `POST /api/ingest`, `POST /api/search` — testing surface ahead of Phase 5/6 tools, per PRD's Day 1 target ("a grounded answer... from the CLI or a bare API endpoint")

### ⚠ Grading criterion
- [x] **Retrieval returns no relevant chunks → model must say so, not guess.** `RetrievedContext.found` (empty results → `False`) is the "decline gracefully" contract the Phase 5 RAG skill will check.

### Testing (write alongside)
- [x] `tests/unit/` — parser, chunker, embeddings (mocked HTTP), retriever ranking, both use cases with a fake `IVectorStore`.
- [x] `tests/integration/` — `/api/ingest`/`/api/search` with a fake vectorstore; the real-Postgres `pgvector_store.py` suite (4 tests) now verified passing against a live Postgres+pgvector container, not just skipping cleanly.

**Deliverable:** `retrieve(query)` returns relevant chunks, provable from a bare script/CLI before the chat UI exists. **This satisfies the PRD's Day 1 target.** Verified against a live Postgres + Ollama (`nomic-embed-text`) pair: migrations applied, 7 real episodes from the ChatPRD/lennys-podcast-transcripts corpus ingested, direct `PgVectorStore.search()` calls return relevant ranked chunks for representative growth/product queries.

**Commit:** `feat: implement document ingestion and retrieval`

---

## Phase 5 — Skills *(Track A, needs Phase 3 + Phase 4 done)*

**Goal:** Each skill works independently, as a **plain callable** — no SDK import, no LLM client, no agent loop (per `docs/ARCHITECTURE.md` §4.7). A skill's job is to prepare grounded material or persist structured output; the model itself, running inside the Phase 6 harness loop, produces the final prose using what the skill returns and the tool-specific instructions below.

### RAG Skill
```
Question → Retriever → grounded context + citations (returned as the tool result)
                              │
     Model composes the cited answer, constrained by the §11.5 RAG prompt
     ("answer only from context, else decline")
```
- [x] `rag_skill.py` returns retrieved chunks + citations + a no-context flag — no model call inside the skill
- [x] No-chunks-found flag from Phase 4 is threaded through so the model can decline honestly

### Ship30 Skill
```
Topic → Retriever (broader pull across relevant episodes) → grounded material (tool result)
                              │
     Model writes the ~1250-word essay, constrained by the §11.5 Ship30 structure
```
- [x] `ship30_skill.py` returns the retrieved material — the essay text itself is the model's own generation in its next turn, not something the skill produces

### Artifact Skill
```
Model composes the Markdown/HTML/CSS and its type as part of the tool call
                              │
     `artifact_skill.py` validates the type, persists {session_id, type, content}, returns artifact_id
```
- [x] `artifact_skill.py` is persistence + validation only — it does not generate content

### ⚠ Grading criterion
- [x] Confirm each skill, tested in isolation (mock `IVectorStore`, fixture chunks, a fake tool-call payload), produces the data the PRD's named success criteria depend on — grounded chunks + citations for RAG, sufficient material for a structurally-correct Ship30 essay, correct validation/persistence for artifacts. See `tests/unit/test_rag_skill.py`, `test_ship30_skill.py`, `test_artifact_skill.py`.

**Deliverable:** Each skill callable and correct on its own (a test script is enough — no harness or Swagger UI needed), independent of the agent harness.

**Commit:** `feat: implement agent skills`

---

## Phase 6 — Agentic Wiring *(Track A)*

**Goal:** Make the system agentic — the model chooses the skill, not our code. There is **no router class and no fallback classifier.** The Claude Agent SDK's native tool-calling *is* the routing; this phase is where the three Phase 5 skills become tools the Phase 3 harness can call.

```
User Message → Harness (Claude Agent SDK) → model picks a tool → tool executes → model composes final reply
```

- [x] `tool_adapters.py` in `infrastructure/harness/` — registers `rag_query`, `write_ship30_essay`, `generate_artifact` as SDK tools, each calling straight into its Phase 5 skill callable
- [x] `agent_sdk_harness.py` is updated to pass the registered tools into the loop (Phase 3 ran with none)
- [~] Verify tool-choice works correctly against **both** Anthropic and Ollama — Ollama tested (see below); Anthropic not yet tested this session (no API key available).

### ⚠ Grading criterion — this is "the agent decides which skill to use"
- [~] Confirm the model's tool choice is correct for a RAG question, a Ship30 request, and an artifact request, on both providers. **Ollama (`qwen3:8b`): tool wiring confirmed correct (SDK registers and connects the MCP server; the CLI's own built-in tools correctly disabled), but the model itself does not reliably emit tool calls even when explicitly instructed to — a real, investigated model-capability limitation, not a wiring bug. See build-log's "Ollama tool-calling verification" entry for the full diagnostic and a recommendation to try a model Ollama documents as tool-calling-capable.** Anthropic: not yet tested (no API key this session) — expected lower-risk per PRD §9.
- [x] **Tool raises or returns malformed output** → caught in `tool_adapters.py`, returned to the loop as a `tool_result` error so the model can recover (verified with unit tests injecting raising fakes); iteration cap enforced via `ClaudeAgentOptions.max_turns=8`. Never surfaces an SDK stack trace to the user.

### Testing (write alongside)
- [x] `tests/unit/` — `tool_adapters.py` error handling: a skill exception becomes a `tool_result` error, not a propagated crash (`test_tool_adapters.py`); iteration cap set via `max_turns`.
- [x] Manual check against Ollama with tools registered — see the "Ollama tool-calling verification" build-log entry above; found real config bugs (fixed) and one model-capability limitation (logged).

**Deliverable:** User doesn't choose the skill; the model does, via the SDK's own loop. Confirmed on Ollama (mechanically — the harness routes correctly to whichever tool the model calls; `qwen3:8b`'s own tool-calling reliability is the open item). Not yet confirmed on Anthropic.

**Commit:** `feat: register skills as harness tools`

---

## Phase 7 — Frontend *(Track A)*

**Goal:** Improve UX around the working backend.

- [ ] Sidebar
- [ ] Session switching
- [ ] Settings page
- [ ] New Chat / Delete Chat / switch session

### ⚠ Grading criterion — wire up the Phase 1 backend behavior here
- [ ] **DB failure banner** in the UI, consuming the 503 built in Phase 1 (don't leave it as backend-only).
- [ ] In-flight messages are not silently dropped on any of the named failure modes.

**Deliverable:** Full session UX works end to end.

**Commit:** `feat: implement chat interface`

---

## Phase 8 — Artifact Viewer *(Track A)*

**Goal:** Assignment requirement — render generated artifacts.

```
Artifact tool call → persisted artifact → Right panel → sandboxed <iframe srcDoc> → Live preview
```

- [ ] Detect type (Markdown vs HTML) from the tool call's structured output, not by parsing raw chat text (per PRD §6.6)
- [ ] Markdown via `react-markdown` + `rehype-sanitize`
- [ ] HTML/CSS via sandboxed `<iframe srcDoc="...">` — never injected into the parent DOM (this is the mitigation for the "unsafe generated script" risk in PRD §9)
- [ ] Viewer opens automatically when an artifact is produced

**Deliverable:** Markdown and HTML/CSS artifacts render side-by-side with chat.

**Commit:** `feat: add artifact viewer`

---

## Phase 9 — Polish, Testing, Docs

By this point, error handling and unit tests for each layer already exist (built alongside Phases 1, 3, 4, 6 — not from scratch here). Phase 9 is genuinely just polish and the remaining PRD-named items that only make sense at the end.

### Polish
- [ ] Streaming (SSE), if time allows — artifacts still render only once a message finishes (per PRD's Day 3 cut)
- [ ] Loading / typing indicators
- [ ] Markdown syntax highlighting

### Testing — fill remaining gaps only
- [ ] Frontend smoke tests (Playwright): send a message → response renders; trigger an artifact → viewer opens (PRD §8)
- [ ] **Manual end-to-end pass:** one full run on Anthropic, one full run on Ollama, exercising all three tools plus one deliberate error case (e.g. stop Ollama mid-conversation). This run doubles as your required "what failed and how you fixed it" content — see below.

### Documentation
- [ ] README — including the Node.js / Claude Code CLI prerequisite confirmed in Phase 3
- [ ] `docs/ARCHITECTURE.md` (already exists — confirm it matches what was actually built)
- [x] `docs/design.md` (embedding-provider decision from Phase 0, harness-vs-provider-hierarchy decision, plus later standing decisions)
- [ ] Demo video

### ⚠ Grading criterion — don't reconstruct this from memory
- [ ] `docs/agent-transcripts/build-log.md` — **populate this throughout the build, not at the end.** Every time something breaks (tool-calling fails on a local model, a migration conflicts, retrieval returns nothing for a valid query, the Agent SDK needs a config tweak against Ollama), jot it down immediately with what failed and how it was fixed. Reconstructing this in Phase 9 from memory loses most of its value and its credibility.

**Deliverable:** Full demo-ready build with docs, tests, and a real (not reconstructed) failure log.

**Commit:** `docs: complete project documentation`

---

## Things deliberately NOT happening

See the canonical list in `CLAUDE.md` → "Scope boundaries — do not build these". It is maintained in one place so it cannot drift; don't restate it here.

You're building a working application first, then layering on intelligence — but error handling, tests, and the agent-transcripts log are built **as you go**, because all three are named grading criteria and none of them survive being deferred to a Phase 9 crunch on a 3-day clock.