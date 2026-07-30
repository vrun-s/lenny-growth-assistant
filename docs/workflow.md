# Workflow Guide — Lenny Growth Assistant

**Timeline:** 3 days (due Aug 2, 2026 EOD)
**Status:** Phases 0 and 1 complete. Phase 2 is next.
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

### Frontend
- [ ] Chat window
- [ ] Input
- [ ] Message history renders

**Deliverable:** You can chat. Messages persist. Reload the page — conversation still exists.

**Commit:** `feat: implement chat workflow`

---

## Phase 3 — Provider Layer *(Track A)*

**Goal:** Replace dummy responses with real LLMs.

- [ ] `BaseProvider` interface (domain port)
- [ ] `AnthropicProvider`
- [ ] `OpenAIProvider`
- [ ] `OllamaProvider`
- [ ] `LLM_PROVIDER=...` env var switches implementation

### ⚠ Grading criterion — build here, not in Phase 9
- [ ] **Missing API key → fail fast at startup**, naming the missing env var. Do this in the provider's `__init__`/config validation, not mid-conversation.
- [ ] **Ollama unreachable / request timeout** → chat-visible error ("Local model didn't respond — is Ollama running?"), configurable timeout (default 30s). This is provider-layer code — write it now while you're inside `OllamaProvider`.

### Testing (write alongside)
- [ ] Mock each provider in `tests/unit/` (this is explicitly named in PRD §8 — don't skip).

**Deliverable:** Changing one env variable changes providers; failure modes above are demonstrable (kill Ollama, unset an API key).

**Commit:** `feat: add configurable LLM providers`

---

## Phase 4 — Knowledge Base (RAG) *(Track B — run in parallel with Phases 1–3)*

**Goal:** Grounded retrieval, no LLM yet. This is the PRD's actual Day 1 deliverable — start it early, don't wait for persistence to finish.

```
Markdown transcripts → Parser → Chunker → Embeddings → pgvector → Retriever
```

- [ ] Parser (`infrastructure/ingestion/parser.py`)
- [ ] Chunker (`infrastructure/ingestion/chunker.py`)
- [ ] Embedder (`infrastructure/ingestion/embedder.py`) — uses the local embedding model decided in Phase 0
- [ ] Loader (`infrastructure/ingestion/loader.py`) → pgvector via `infrastructure/vectorstore/pgvector_store.py`
- [ ] Retriever (`infrastructure/vectorstore/retriever.py`)
- [ ] Standalone CLI entrypoint: `scripts/run_ingestion.py` (zero business logic — just calls into `infrastructure/ingestion/`, per ARCHITECTURE.md §5)

### ⚠ Grading criterion
- [ ] **Retrieval returns no relevant chunks → model must say so, not guess.** Build the "decline gracefully" behavior into the retriever's contract now (e.g. return empty + a flag) so the RAG skill in Phase 5 has something to check.

### Testing (write alongside)
- [ ] `tests/unit/` — retrieval function against a small fixture set of transcript chunks (named explicitly in PRD §8).

**Deliverable:** `retrieve(query)` returns relevant chunks, provable from a bare script/CLI before the chat UI exists. **This satisfies the PRD's Day 1 target.**

**Commit:** `feat: implement document ingestion and retrieval`

---

## Phase 5 — Skills *(Track A, needs Phase 3 + Phase 4 done)*

**Goal:** Each skill works independently. Do not build routing yet.

### RAG Skill
```
Question → Retriever → Prompt (§11.5 template) → Provider → Answer (cited)
```
- [ ] Apply the "answer only from context, else decline" prompt template
- [ ] Wire in the no-chunks-found decline behavior from Phase 4

### Ship30 Skill
```
Prompt → Ship30 template (§11.5) → Provider → ~1250-word essay
```

### Artifact Skill
```
Prompt → Generate HTML/Markdown → Save artifact → Return artifact ID
```

### ⚠ Grading criterion
- [ ] Confirm each skill, tested in isolation, produces the PRD's named success criteria (grounded + cited RAG answers; Ship30 essay matches structure/length; artifact is valid Markdown or HTML/CSS in a single fenced block).

**Deliverable:** Each skill callable and correct on its own (e.g. via a test script or Swagger UI), independent of routing.

**Commit:** `feat: implement agent skills`

---

## Phase 6 — Router *(Track A)*

**Goal:** Make the system agentic — the model chooses the skill, not the user.

```
User Message → Router → Which skill? → Execute skill → Return response
```

- [ ] Cloud providers (Anthropic/OpenAI): native tool-calling with the three tools from PRD §6.5
- [ ] Ollama: try native tool-calling first if the model supports it

### ⚠ Grading criterion — this is the fallback path the PRD calls "the biggest risk to the mandatory local demo"
- [ ] **Malformed tool-call output → fallback prompted classifier** (`RAG | SHIP30 | ARTIFACT | GENERAL`), parsed defensively, default to `RAG` on any parse failure. Build this now, in the router — not surfaced as a raw error.

### Testing (write alongside)
- [ ] `tests/unit/` — router's fallback logic (named explicitly in PRD §8: test malformed output → correct fallback classification).

**Deliverable:** User doesn't choose the skill; the agent does — provable on both Anthropic and Ollama.

**Commit:** `feat: implement agent routing`

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
Artifact Skill returns artifact → Right panel → sandboxed <iframe srcDoc> → Live preview
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
- [ ] **Manual end-to-end pass:** one full run on Anthropic, one full run on Ollama, exercising all three skills plus one deliberate error case (e.g. stop Ollama mid-conversation). This run doubles as your required "what failed and how you fixed it" content — see below.

### Documentation
- [ ] README
- [ ] `docs/ARCHITECTURE.md` (already exists — confirm it matches what was actually built)
- [x] `docs/design.md` (embedding-provider decision from Phase 0 recorded, plus later standing decisions)
- [ ] Demo video

### ⚠ Grading criterion — don't reconstruct this from memory
- [ ] `docs/agent-transcripts/build-log.md` — **populate this throughout the build, not at the end.** Every time something breaks (tool-calling fails on a local model, a migration conflicts, retrieval returns nothing for a valid query), jot it down immediately with what failed and how it was fixed. Reconstructing this in Phase 9 from memory loses most of its value and its credibility.

**Deliverable:** Full demo-ready build with docs, tests, and a real (not reconstructed) failure log.

**Commit:** `docs: complete project documentation`

---

## Things deliberately NOT happening

See the canonical list in `CLAUDE.md` → "Scope boundaries — do not build these". It is maintained in one place so it cannot drift; don't restate it here.

You're building a working application first, then layering on intelligence — but error handling, tests, and the agent-transcripts log are built **as you go**, because all three are named grading criteria and none of them survive being deferred to a Phase 9 crunch on a 3-day clock.
