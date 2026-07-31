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

---

## Phase 3 built harness-only, with zero tools registered (2026-07-30)

**Decision:** `IAgentHarness`, `AgentResult`, and `AgentSdkHarness` were implemented and wired into `SendMessageUseCase`/`chat_router`, but `infrastructure/harness/tool_adapters.py` was **not** created and no tools are registered with `ClaudeAgentOptions` yet. `rag_skill.py`, `ship30_skill.py`, and `artifact_skill.py` exist as plain-callable placeholders that raise `NotImplementedError` with a message pointing at the missing dependency (`infrastructure/vectorstore` for the first two, an `IArtifactRepository` port for the third).

**Why:** Phase 4 (ingestion + `IVectorStore`/pgvector retrieval) doesn't exist yet, so `rag_skill`/`ship30_skill` would have nothing real to retrieve from. The alternative — a temporary in-memory/fake vector store to demo tool-calling early — was explicitly rejected: it's a throwaway implementation that would need to be torn out again once Phase 4 lands, and it risks masking a real retrieval bug behind fake data that always "works." Matches `workflow.md`'s existing phase order (Phase 3 → 4 → 5 → 6) and its own stated Phase 3 scope: "runs a turn with no tools yet."

**Consequence:** the harness currently answers from the model's own knowledge with no grounding, since there are no tools to call. This is expected and temporary — do not treat it as the RAG grounding requirement being met. Tool registration and real skill bodies land together once Phase 4 is done.

**LLM_PROVIDER → base_url resolution, concretely:** `core/config.py`'s `Settings.harness_base_url`/`harness_model`/`harness_api_key` properties resolve the toggle. Because the Claude Agent SDK wraps the Claude Code CLI as a subprocess rather than calling the Anthropic Messages API directly in-process, there's no `base_url` field on `ClaudeAgentOptions` — the Ollama endpoint is passed via `ANTHROPIC_BASE_URL`/`ANTHROPIC_API_KEY` in `ClaudeAgentOptions.env`, which the CLI subprocess reads the same way it would from a shell environment.

**Fail-fast on missing `ANTHROPIC_API_KEY`:** implemented as a Pydantic `model_validator(mode="after")` on `Settings`, so `get_settings()` — called once at `create_app()` startup — raises `ValidationError` immediately when `LLM_PROVIDER=anthropic` and no key is set, rather than failing on the first chat request. Tests need a dummy key via an autouse `conftest.py` fixture as a result (see `docs/agent-transcripts/build-log.md`).

**Ollama unreachable / harness timeout:** `AgentSdkHarness.run()` wraps the async SDK call in `asyncio.wait_for(..., timeout=settings.harness_timeout_seconds)` (default 30s) and maps both timeouts and connection failures to a new domain exception, `HarnessUnavailableError`, mapped to HTTP 502 in `app.py` with the exact chat-visible message from `ARCHITECTURE.md`/PRD §7.1 ("Local model didn't respond — is Ollama running?" for Ollama).

---

## Phase 4A: single `documents` table, not three (2026-07-30)

**Decision:** One `documents` table, exactly as PRD §11.3 specifies (`id, title, source, episode, speaker, timestamp_range, chunk, embedding vector(768)`) — no separate `document_chunks`/`embeddings` tables. `infrastructure/vectorstore/pgvector_store.py` owns this table via its own `DeclarativeBase`, independent of `infrastructure/database/orm_models.py`'s `Base`.

**Why:** PRD §11.3 is the frozen, already-decided schema, and a three-table split isn't in it — a chunk *is* a `Document` in this schema (there's no separate parent-document concept above the chunk level), and each chunk already carries exactly one embedding, so a chunk table and an embeddings table would be a 1:1 split with no independent lifecycle, i.e. a new abstraction the "architecture frozen / don't introduce new abstractions" instruction rules out. Splitting `pgvector_store.py`'s table definition from `infrastructure/database/orm_models.py`'s `Base` is required by ARCHITECTURE.md §4.3 ("pgvector-specific ORM/queries must never appear outside infrastructure/vectorstore/") and §2.2 (infra sub-modules must not import one another) — consequence: the `documents` migration (`0365a449c420`) is hand-written, not autogenerated, since `alembic/env.py`'s `target_metadata` only points at `orm_models.Base`. Documented in the migration file itself so this doesn't get "fixed" into an autogenerate diff later.

## Phase 4A: embedding stays solely in `infrastructure/vectorstore/embeddings.py` (2026-07-30)

**Decision:** `infrastructure/ingestion/embedder.py` (named in ARCHITECTURE.md's tree) is left as an empty stub. `IVectorStore.add_documents()` embeds any document that doesn't already carry a vector, internally, using `infrastructure/vectorstore/embeddings.py`'s `OllamaEmbedder` — the same class `search()` uses to embed the query. Ingestion (`parser.py` → `chunker.py` → `loader.py`) never touches embeddings at all; it produces `Document`s with `embedding=None`.

**Why:** Two embedding-calling modules for the same Ollama endpoint would either duplicate the HTTP call (drift risk — the model name or dimension could diverge between the two) or require `infrastructure/ingestion/` to import `infrastructure/vectorstore/`, which ARCHITECTURE.md §2.2 forbids (infra sub-modules must not import one another directly, no documented exception for this pair). Keeping the *port* boundary at `IVectorStore.add_documents(documents_without_embeddings)` rather than "ingestion embeds, then hands pre-embedded documents to the store" also matches the existing comment on `Document.embedding` ("retrieval has no reason to carry a 768-float vector back up through the layers") — the same reasoning extends to ingestion not needing to touch raw vectors either.

## Phase 4A: `retriever.py` vs `pgvector_store.py` split (2026-07-30)

**Decision:** `pgvector_store.py` owns the SQLAlchemy engine, the `DocumentModel`, and executes the cosine-distance query; `retriever.py` is a pure function (`rank_results`) that converts raw query-result rows into `SearchResult`s. Both live in `infrastructure/vectorstore/` (same sub-module, so no cross-import concern), matching workflow.md Phase 4's checklist listing them as separate items ("Loader → pgvector via pgvector_store.py" / "Retriever (retriever.py)").

**Why:** Keeps the one part of retrieval that's meaningfully unit-testable without a database (row → `SearchResult` shaping, including the distance→similarity-score conversion) separate from the part that requires a live Postgres connection — `tests/unit/test_retriever.py` covers the former with zero infrastructure; `tests/integration/test_pgvector_store.py` covers the latter and skips cleanly when Postgres isn't running.

## Phase 4A: `IngestDocumentsUseCase`/`RetrieveContextUseCase` earn their layer (2026-07-30)

**Decision:** `IngestDocumentsUseCase` validates non-empty chunk text and dedupes by ID within a batch before calling `IVectorStore.add_documents()`. `RetrieveContextUseCase` clamps `top_k` to `[1, 20]` and wraps the result in `RetrievedContext` (with a `found` property) before returning.

**Why:** `design.md`'s existing "use cases are added when they hold logic, not by default" decision means a pure `return self._vectorstore.search(query, top_k)` forwarder wouldn't earn a use case — the router would call `IVectorStore` directly, the way `session_router` already calls `ISessionRepository` for list/delete. Both use cases here hold a real invariant instead: a data-integrity check for ingestion, and the "decline gracefully when nothing is relevant" contract for retrieval (an explicit PRD §7.1 grading criterion) for retrieval. That's what justifies their existence as use cases rather than direct router→port calls.

---

## Phase 4B: parser adapted for the real ChatPRD/lennys-podcast-transcripts corpus format (2026-07-31)

**Decision:** `infrastructure/ingestion/parser.py` now supports two transcript conventions instead of one. The original inline `**[timestamp] Speaker:** text` convention this parser was written against is kept as-is (existing unit tests are unchanged). Added on top: a YAML frontmatter block (`_split_frontmatter`, parsed with `pyyaml`) supplying `title`/`youtube_url`, and a `Speaker (HH:MM:SS):` header line followed by the turn's text on the next line(s) — the actual format used by every episode in the real archive (github.com/ChatPRD/lennys-podcast-transcripts). A header line with no speaker name (`(00:01:51):`) is a continuation and carries the previous speaker forward, rather than being recorded as speaker=None — this matches how the source transcribes a single speaker's multi-paragraph turn.

**Why:** The real corpus (cloned and inspected directly) does not use the inline convention at all — no `**Source:**` line, and turns are `Speaker (timestamp):\ntext`, not same-line. Frontmatter carries `title`/`youtube_url` instead of an inline heading/source line. "Adapt, don't replace" was the instruction (workflow.md's Implementation Scope), so the fix is additive: a new frontmatter-split step ahead of parsing, plus a second segment-header regex tried alongside the original inline one, sharing the same `TranscriptSegment`/`ParsedTranscript` shapes and the same chunker/loader downstream. All 13 original parser/chunker unit tests pass unmodified.

**New runtime dependency:** `pyyaml==6.0.2`, added to `backend/requirements.txt`. Frontmatter parsing needs a real YAML parser (the `description` field is a multi-line block scalar, `keywords` is a list) — a regex-only frontmatter reader would be fragile against that.

---

## Phase 4B: `IAgentHarness.run()` gains a `session_id` parameter (2026-07-31)

**Decision:** `IAgentHarness.run(history, user_message, session_id)` — additive parameter, not a redesign. `SendMessageUseCase` (which already has `session_id`) passes it through; `AgentSdkHarness` forwards it to `tool_adapters.build_tool_server()` for that turn.

**Why:** The `generate_artifact` tool must persist `Artifact.session_id` correctly, and the harness has no other way to learn which session a turn belongs to — `AgentResult`/`IAgentHarness` predate any tool needing session context. CLAUDE.md's "ports before adapters" rule ("If a use case or skill needs a new capability... define/extend the interface in `domain/interfaces/` first") explicitly sanctions this: extend the port, don't smuggle `session_id` through a global or a second channel. The alternative — persisting the artifact in `SendMessageUseCase` after `run()` returns, using an artifact-shaped value without a session tie — would have left `artifact_skill.py` unable to satisfy its own stated job ("validates the type, persists {session_id, type, content}").

**Consequence:** both `FakeAgentHarness` test doubles (`test_send_message_use_case.py`, `test_chat_router.py`) and the port docstring were updated to the 3-arg signature.

---

## Phase 4B: tool registration — one in-process MCP server built fresh per turn (2026-07-31)

**Decision:** `infrastructure/harness/tool_adapters.py` uses `claude_agent_sdk.tool` + `create_sdk_mcp_server` to register `rag_query`, `write_ship30_essay`, and `generate_artifact` as an in-process SDK MCP server (`McpSdkServerConfig`), passed to `ClaudeAgentOptions.mcp_servers` alongside `allowed_tools=["mcp__lenny_tools__<name>", ...]`. `AgentSdkHarness._run_async()` calls `build_tool_server(...)` on every turn rather than once at construction time, closing the handlers over that turn's `session_id`, `RetrieveContextUseCase`, and `IArtifactRepository`.

**Why:** SDK MCP tools are plain async functions that close over whatever they need — there's no per-call argument for "current session" the SDK threads through, so the closure has to be built with the right session_id already baked in, which changes every turn. Rebuilding per turn is cheap (no network/process spin-up — it's an in-process server) and avoids a stale-session bug from reusing one server built with an earlier turn's session_id.

**Tool logic vs. tool registration split:** each handler's actual work (`rag_query()`, `write_ship30_essay()`, `generate_artifact()`) is unchanged plain-callable code in `application/skills/`, taking no SDK types. `tool_adapters.py` owns: the `@tool` decorator/JSON schema, catching the skill's exceptions and turning them into `{"is_error": True, ...}` tool_results (PRD §7.1 — a tool exception must reach the model as a recoverable `tool_result`, never propagate as a crash), and capturing citations/the persisted `Artifact` into a per-turn `ToolRunResults` box that `agent_sdk_harness.py` reads back after the loop to populate `AgentResult.citations`/`AgentResult.artifact`. The three `handle_*` functions in `tool_adapters.py` are separated from the `@tool`-decorated closures specifically so they're unit-testable directly (`tests/unit/test_tool_adapters.py`) without exercising the SDK's own tool-dispatch machinery.

**Iteration cap:** `ClaudeAgentOptions.max_turns=8` on every request (`agent_sdk_harness.MAX_TURNS`) — the SDK's own bound, not a hand-rolled loop counter, satisfying PRD §7.1's "iteration cap prevents runaway loops" without writing loop-control code this project isn't supposed to own.

**API surface consequence:** `ChatResponse` gained `citations: list[str]` and `artifact_id: UUID | None` so the values `AgentResult` now actually carries aren't silently dropped at the API boundary — needed by Phase 8's artifact viewer and the citation requirement in PRD §11.5, not new scope invented here.

---

## Phase 4B/6: `ClaudeAgentOptions` locked down to only the three registered tools (2026-07-31)

**Decision:** `AgentSdkHarness` now always sets `tools=[]` (disables the Claude Code CLI's own built-in tool belt — `Bash`, `Edit`, `Read`, `Write`, `Task`, etc.) and `permission_mode="bypassPermissions"`. When `LLM_PROVIDER=ollama`, it additionally sets `options.thinking = {"type": "disabled"}`.

**Why:** Discovered while running the harness against Ollama for the first time with real tools registered (see build-log). Without `tools=[]`, every turn silently carried the CLI's entire built-in tool set alongside the three domain tools — invisible in Phase 3 (nothing to compare against, since no tools existed yet) and only surfaced once `qwen3:8b` visibly hallucinated a coding-workflow response to a simple prompt, revealing it was seeing Claude Code's own tool/system context. This is a correctness and safety fix for **both** providers, not just Ollama — a growth advisor answering from Lenny's transcripts must never have Bash/filesystem access, regardless of which model is behind it. `permission_mode="bypassPermissions"` is required because the default mode blocks on an interactive approval prompt before any tool executes, which hangs forever in a headless backend request with no human to answer it — our own three tools are internally validated (type-checked, exception-mapped to `tool_result` errors) so bypassing the prompt is safe. Thinking is disabled only for Ollama because local reasoning models are slow enough on CPU that extended chain-of-thought made even a bare "say hi" query take ~30s; Anthropic's models don't have this problem and keep full thinking.

**Known limitation, not a bug to fix here:** `qwen3:8b` (the only tool-capable model pulled in this environment) does not reliably emit a `tool_use` block through the full SDK/CLI conversation path, even when explicitly instructed to call a named tool — confirmed via a multi-step diagnostic in `docs/agent-transcripts/build-log.md`, including proof that the same model *does* return a correct `tool_use` block against Ollama's raw `/v1/messages` endpoint outside the CLI. Per the standing "no fallback harness" decision above, this is logged rather than worked around with a keyword-forcing shim (explicitly a cancelled approach) or a second harness. Plain (toolless) conversation against Ollama works correctly once the three options above were fixed.

---

## Dedicated test database, transaction-rollback isolation (2026-07-31)

**Problem:** `tests/integration/test_pgvector_store.py`'s `store` fixture ran an unscoped `session.query(DocumentModel).delete()` against the real `documents` table before *and* after every test — correct for isolating the test suite against itself, but destructive whenever tests and real ingestion shared one Postgres database. This happened twice in one session (logged above, "Real ingestion silently wiped by the pgvector test fixture running concurrently"): a bulk-ingestion run's committed rows were wiped mid-run by a concurrent `pytest -q`, and — after restarting ingestion clean — the same class of accident happened a second time immediately after, running the full suite right after confirming a 741-row corpus. Procedural workarounds ("don't run tests while ingesting") don't hold up; the DB itself needs to make the accident structurally impossible.

**Decision:** Postgres-backed tests now run against a second, dedicated database (`lenny_growth_assistant_test`) in the same `pgvector/pgvector:pg16` container — not a second container, not a second docker-compose service. `deployment/init/02-create-test-db.sql` creates it (`CREATE DATABASE ... WHERE NOT EXISTS`, via `psql`'s `\gexec`) and enables the `vector` extension inside it, alongside the existing `enable-pgvector.sql` for the dev database. `core/config.py` gained `Settings.test_database_url`, independent of `database_url`, documented in the new `backend/.env.example`.

`backend/tests/conftest.py` replaces the delete-based cleanup with connection-scoped transaction rollback: a session-scoped `pg_test_engine` fixture (built from `test_database_url`, schema created once via `Base.metadata.create_all` + `_VectorBase.metadata.create_all`, skips dependent tests if unreachable) backs a per-test `pg_connection` fixture that opens a connection, begins a transaction, yields it, then rolls back and closes — so nothing a test writes is ever committed. `PgVectorStore` gained an optional `engine: Engine | Connection | None` constructor parameter (alongside the existing `database_url` parameter, which production code keeps using) so its internal `sessionmaker` can bind to that same open connection instead of building a fresh engine from a URL; without this, `add_documents()`/`search()` opening their own sessions against a plain `Engine` would each grab a different pooled connection and not see each other's uncommitted writes within one test, let alone roll back together. `test_pgvector_store.py`'s `store` fixture now takes `pg_connection` and no longer constructs its own engine, skip logic, or delete calls.

A hard safety assertion runs before the session-scoped engine is even created: if `database_url == test_database_url`, or the two URLs parse (via `sqlalchemy.engine.make_url`) to the same database name, `conftest.py` raises `RuntimeError` immediately. This is a raise, not a skip — a misconfigured `.env` must fail the whole run loudly rather than quietly proceeding against the wrong database.

**Why:** Rollback isolation removes the entire class of bug: a test can never leave committed rows behind, so there's nothing to accidentally delete-collide with concurrent or subsequent real ingestion, and the safety assertion means even a config mistake (e.g. someone unsetting `TEST_DATABASE_URL` so it falls back to matching `DATABASE_URL`) can't silently degrade back into the old shared-database failure mode. Keeping it a second database in the same container (not a second container/service) matches the project's "same Postgres, just a second database" constraint and needs no new docker-compose service, credentials, or CI wiring.

**Consequence:** any future Postgres-backed integration test must use `pg_connection`/`pg_session` from `conftest.py` rather than constructing its own engine — `test_pgvector_store.py` is the only current example, but the pattern generalizes. `PgVectorStore(engine=...)` is a small, additive infra change (not new abstraction — one optional constructor parameter) that exists solely to make the store's sessions joinable to an externally-managed transaction; production code paths (`scripts/run_ingestion.py`, `infrastructure/api/deps.py`) are unaffected since they still pass `database_url`/rely on the default.

**Revisit when:** a second Postgres-backed test file is added — confirm it reuses `pg_connection`/`pg_session` rather than re-deriving its own engine-and-skip boilerplate.