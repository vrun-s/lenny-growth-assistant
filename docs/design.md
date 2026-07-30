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
