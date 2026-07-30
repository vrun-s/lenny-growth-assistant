# Design Decisions

Standing decisions that should not be re-litigated per feature. If a decision changes, update it here with the date and reason — don't just start doing something different.

---

## Embedding provider: `nomic-embed-text` via Ollama

**Decision:** Embeddings are generated locally using `nomic-embed-text` served through Ollama. No cloud embeddings API (OpenAI, Voyage, Cohere, etc.) is used anywhere in the pipeline, including when `LLM_PROVIDER=anthropic` or `LLM_PROVIDER=openai`.

**Why:** The offline requirement (PRD §7 — "full pipeline must run with `LLM_PROVIDER=ollama` and no internet access after initial model pull") only holds if retrieval doesn't secretly depend on a network call. Splitting "chat provider" from "embedding provider" would mean the app silently breaks offline even though the chat toggle says `ollama`. Using the same local stack for embeddings regardless of chat provider keeps ingestion and retrieval provider-independent and removes a second API key / billing surface to configure.

**How it's used:**
- `infrastructure/vectorstore/embeddings.py` calls Ollama's `/api/embeddings` endpoint with model `nomic-embed-text` (768 dimensions).
- The pgvector column is fixed at `vector(768)` to match. If the embedding model ever changes, existing vectors must be re-embedded — dimension is not dynamic.
- Ollama must be running locally (`ollama pull nomic-embed-text`) for ingestion and retrieval to work, even when chatting against Anthropic/OpenAI.
- Chunking/embedding batch size is kept small (single request per chunk) since this is a solo/local project, not a throughput-optimized pipeline — revisit only if ingestion becomes a bottleneck.

**Alternative considered:** local `sentence-transformers` (e.g. `all-MiniLM-L6-v2`) run in-process via the `sentence-transformers` Python package. Rejected for now to avoid adding a second local runtime dependency (PyTorch) alongside Ollama, which is already required for the local LLM toggle. Revisit only if Ollama's embeddings endpoint proves unreliable.

---

## Frontend stack scaffolding (Phase 0)

**Decision:** React + Vite + TypeScript, `react-router-dom` for client-side routing, Tailwind CSS v4 via the `@tailwindcss/vite` plugin (no separate PostCSS config needed). `shadcn/ui` components are added incrementally as needed per Phase 1+ feature, not pre-installed wholesale in Phase 0 — its CLI copies components into `shared/components/` on demand rather than being a single dependency to bootstrap up front.

**Why:** Matches the stack committed to in `ARCHITECTURE.md` / `CLAUDE.md`. Tailwind v4's Vite plugin avoids a `tailwind.config.js` + `postcss.config.js` pair for a project this size.

**Dev server:** Vite dev server proxies `/api/*` to `http://localhost:8000` (see `frontend/vite.config.ts`), so the frontend API client can call relative paths (`API_BASE_URL = '/api'`) without hardcoding a backend origin. In production, `VITE_API_BASE_URL` overrides this.

---

## Local Postgres + pgvector (Phase 0)

**Decision:** `deployment/docker-compose.yml` runs a single `pgvector/pgvector:pg16` container (Postgres 16 with the pgvector extension pre-built in). The `vector` extension is enabled via an init script (`deployment/init/enable-pgvector.sql`) mounted into `/docker-entrypoint-initdb.d/`, run automatically on first container start.

**Why:** Avoids a separate `CREATE EXTENSION` migration step before Alembic can run, and avoids maintaining a custom Postgres image — `pgvector/pgvector` is the upstream-maintained image for this exact use case.

**Local credentials** (`lenny` / `lenny` / db `lenny_growth_assistant`) are dev-only defaults, not meant to be reused anywhere else — this is a local-first evaluation project, not a deployed service.

---

## Use cases are added when they hold logic, not by default (2026-07-30)

**Decision:** A use case class exists only where there is orchestration to hold — generating identity/timestamps, coordinating more than one port, or enforcing an invariant. Where a router operation is a straight pass-through to a single repository method, the router calls the repository port directly. `CreateSessionUseCase` stays (it mints the UUID, timestamps, and default title); `ListSessionsUseCase` and `DeleteSessionUseCase` were removed as pure forwarding.

**Why:** Both removed classes were a constructor plus a one-line `execute()` that returned `self._repo.<same method>(...)`. That is indirection, not a layer — it costs a file, an import, and a router-side instantiation to buy nothing, and it makes the genuinely-useful `CreateSessionUseCase` harder to notice. The dependency rule is unaffected: routers depend on `domain/interfaces/`, never on a concrete repository class, so the arrow still points inward. Codified as ARCHITECTURE.md §4.6.

**Revisit when:** an operation grows real logic (e.g. delete needing to cascade artifacts through a second port, or list needing pagination/filtering). Add the use case then.

---

## Enum columns persist values, not member names (2026-07-30)

**Decision:** `MessageRole` and `ArtifactType` columns are declared with `values_callable=lambda e: [m.value for m in e]`, so Postgres stores `user`/`assistant` and `markdown`/`html`.

**Why:** SQLAlchemy's `Enum` defaults to persisting the *member name*, which would have written `USER` and `MARKDOWN` — disagreeing with the schema documented in PRD §11.3, with the `str` values on the domain enums, and with whatever the API serializes. The mismatch is invisible until something compares a stored value to a literal.

**Consequence:** the initial migration `f144a33b5570` was corrected in place rather than superseded, since it is the only migration and no shared environment depends on it. Anyone with a database created before this change must rebuild it (`docker compose down -v && docker compose up -d`, then `alembic upgrade head`).

---

## Frontend `strict` mode is on (2026-07-30)

**Decision:** `"strict": true` in both `tsconfig.app.json` and `tsconfig.node.json`.

**Why:** It was absent while every other strictness flag the Vite template ships (`noUnusedLocals`, `noUnusedParameters`, `erasableSyntaxOnly`, `noFallthroughCasesInSwitch`) was present — so the codebase was paying for strictness ergonomics without getting null-safety. Turning it on while the frontend is still two placeholder pages costs nothing; turning it on in Phase 7 would not.

---

## API route prefix: `/api`, one prefix for the whole backend (2026-07-30)

**Decision:** `infrastructure/api/app.py` mounts every `v1` router under a single `/api` prefix (`app.include_router(session_router, prefix="/api")`). Phase 2's `chat_router` is mounted the same way, giving `POST /api/chat` and `GET /api/sessions/{id}` alongside the existing `/api/sessions` endpoints. No router declares its own `/api` — each router's own `prefix` (`/sessions`, `/chat`) only names the resource, and `app.py` is the single place that decides the mount point.

**Why:** The Vite dev proxy (`frontend/vite.config.ts`) forwards `/api/*` to the backend verbatim (no path rewrite), and the frontend's `api_client.ts` already hardcodes `API_BASE_URL = '/api'`. A second, inconsistent prefix on a new router would silently 404 from the frontend's perspective while working fine from `curl`. Checked before writing any Phase 2 code rather than assumed.

## The Claude Agent SDK is the harness; we do not write an agent loop (2026-07-30)

**Decision:** The agent loop is owned by the Claude Agent SDK, integrated in `infrastructure/harness/`. The planned `application/skills/router.py` is cancelled. The three skills become tools registered with the SDK: their *logic* stays in `application/skills/` as plain callables, their *registration* (SDK decorators, JSON schemas, in-process MCP server) lives in `infrastructure/harness/tool_adapters.py`. The `BaseProvider → AnthropicProvider | OpenAIProvider | OllamaProvider` hierarchy is cancelled and replaced by a single `IAgentHarness` port. OpenAI is dropped entirely.

**Why:** The brief says to build the API *on top of* the Claude SDK or Pi Coding Agent, and the clarification confirmed this means adopting a harness and improving it — not importing an SDK as one of several LLM clients while hand-rolling the loop. "Harness" (owns the loop) and "orchestration" (owns what the tools do, persistence, grounding) are distinct layers; the cancelled router conflated them by putting an agent loop in the business layer. The replacement is also *less* code: one harness adapter plus thin tool wrappers, versus a router plus three provider classes.

**How the toggle survives:** `LLM_PROVIDER` remains the single switch, but it now resolves to a base URL + model name rather than selecting a class. Ollama v0.14.0+ exposes an Anthropic-compatible `/v1/messages` endpoint including tool use, so `LLM_PROVIDER=ollama` points the same client at `http://localhost:11434` with a dummy key. Same harness, same tools, both paths.

**Consequences:**
- `domain/interfaces/llm_provider.py` becomes `agent_harness.py` (`IAgentHarness.run(...) -> AgentResult`).
- `infrastructure/providers/` is deleted; `infrastructure/harness/` replaces it.
- A new domain entity `AgentResult` (text + citations + optional artifact) is the harness return type, keeping SDK message objects out of the inner layers.
- Session state must be bridged to Postgres explicitly — the SDK's own session handling is process-local and would not survive a backend restart (PRD §7).
- Invariant to enforce: `grep -r "claude_agent_sdk" backend/app/application backend/app/domain` returns nothing.
- Embeddings are untouched — still `nomic-embed-text` via Ollama regardless of chat provider, which is what keeps the offline guarantee true.

**No fallback harness.** An earlier revision of this document included a second `messages_api_harness.py` as insurance against the SDK misbehaving against Ollama. That was over-engineering: Ollama v0.14.0+ exposes a documented, tested Anthropic-compatible `/v1/messages` endpoint including tool use, and the reported issues were about the Claude Code CLI — not the Agent SDK used programmatically. A second loop is real build time spent on a contingency that probably never fires. The correct response to an actual incompatibility is disabling the specific SDK feature that causes it, tested on Day 2 morning. `IAgentHarness` still earns its place as the port you mock in unit tests.

**Alternative considered:** Pi Coding Agent as the harness. The evaluator explicitly allows either. Rejected because Pi is TypeScript-first and oriented around read/write/edit/bash coding tools, which would mean either a second runtime beside the Python backend or reshaping a coding harness into a RAG/essay backend. The Claude Agent SDK has a first-party Python package and the Anthropic-compatible endpoint story that makes the mandatory Ollama path work with the same tool definitions.

**Revisit when:** the Agent SDK proves fundamentally unworkable against Ollama despite config-level fixes — at that point, reconsider Pi. Record the outcome in `docs/agent-transcripts/` regardless; the attempt and its result are a required deliverable.