# CLAUDE.md

Guidance for Claude Code (and any other agent) working in this repository. This file distills `docs/ARCHITECTURE.md` and `docs/PRD.md` — read those for full detail; this is the operational summary to follow on every change.

---

## Project in one paragraph

**Lenny Growth Assistant** — a conversational AI assistant that answers product/growth questions grounded in Lenny's Podcast transcripts (RAG), writes Ship30for30-style essays, and generates Markdown/HTML artifacts, routed automatically by an LLM tool-choice router (with a fallback classifier for local models). Solo build, ~3-day timeline, local-first evaluation project — not production infrastructure. **When in doubt, choose the simpler option.**

---

## Non-negotiable architecture rule: dependencies point inward only

```
INFRASTRUCTURE (adapters: API, DB, providers, vectorstore)
        ↓ imports
APPLICATION (use cases, agent skills)
        ↓ imports
DOMAIN (entities, port interfaces) — zero framework dependencies
```

- `domain/` never imports FastAPI, SQLAlchemy, Pydantic, Alembic, or any provider SDK. Entities are plain `dataclasses`, not `BaseModel`/`Base` subclasses.
- `application/` (use cases + skills) only imports `domain/entities/` and `domain/interfaces/`. It must **never** import a concrete class from `infrastructure/` (no repository classes, no provider SDK clients, no routers). It talks to the outside world only through the abstract interfaces (ports) declared in `domain/interfaces/`.
- `infrastructure/` implements those ports and is the only place framework code and concrete adapters live.
- `core/` (config, logging, constants) has no dependency on `application/`, `domain/`, or `infrastructure/` — it's pure bootstrapping.
- Sub-modules inside `infrastructure/` must not import each other directly (e.g. `vectorstore/` must not call `database/` — go through a use case if data needs to cross that boundary).
- `backend/` never imports from `frontend/` or `scripts/`; `frontend/` never imports from `backend/` or `scripts/` (it talks to the API over HTTP/SSE only).
- `scripts/` are thin CLI runners only — no business logic. Ingestion parsing/chunking/embedding logic lives in `infrastructure/ingestion/`, never inline in a script.

**Before adding code, ask:** which layer does this belong to, and does it only import from layers below it? If you're about to import a concrete infrastructure class into `application/`, stop — define or reuse a port instead.

---

## Repo layout (follow exactly — see ARCHITECTURE.md §3 for the full tree)

```
docs/                    markdown only, no code
deployment/              Docker/compose, no app code
scripts/                 CLI entrypoints only (run_ingestion.py, seed_database.py)
backend/app/
  core/                  config, logging, constants — stdlib + Pydantic only
  domain/
    entities/            Session, Message, Artifact, Document (pure dataclasses)
    interfaces/          repositories.py, llm_provider.py, vectorstore.py (ABCs)
  application/
    use_cases/           create_session, send_message, write_ship30, generate_artifact
    skills/              rag_skill.py, ship30_skill.py, artifact_skill.py, router.py
  infrastructure/
    api/                 FastAPI routers + deps.py (DI happens here)
    database/            SQLAlchemy models + repositories (only place raw queries live)
    providers/           anthropic_provider.py, openai_provider.py, ollama_provider.py
    vectorstore/         embeddings.py, retriever.py, pgvector_store.py (only place vector ops live)
    ingestion/           parser.py, chunker.py, embedder.py, loader.py
  tests/                 unit/, integration/, conftest.py
frontend/src/
  core/                  api client, constants
  features/{chat,artifacts,settings}/
  shared/                design system components/layouts
```

Deliberately **not present** and not to be reintroduced: `container.py` / DI framework, `BaseSkill` abstraction, skill registry, ChromaDB, Monaco Editor.

---

## Tech stack (don't substitute without a reason written in `docs/design.md`)

- **Frontend:** React + Vite + TypeScript + TailwindCSS + shadcn/ui + `react-markdown` + `rehype-sanitize`; HTML/CSS artifacts render in a sandboxed `<iframe srcDoc>` — never injected into the parent DOM.
- **Backend:** FastAPI + SQLAlchemy + Pydantic + Alembic.
- **Database:** PostgreSQL + pgvector — single database, no second vector store.
- **LLM layer:** `BaseProvider` port → `AnthropicProvider` / `OpenAIProvider` / `OllamaProvider`, selected by `LLM_PROVIDER` env var.
- **Embeddings:** must be a **local** model (e.g. `nomic-embed-text` via Ollama, or local `sentence-transformers`) — using a cloud embeddings API silently breaks the offline requirement for `LLM_PROVIDER=ollama`. Decide once, write it in `docs/design.md`, don't re-litigate per feature.
- **DI:** FastAPI's native `Depends` in `infrastructure/api/deps.py` only. No enterprise container.

---

## Database schema (see PRD §11.3 for full field lists)

`ChatSession`, `Messages` (role, content, optional `artifact_id`), `Artifacts` (type: markdown|html), `Documents` (transcript chunks — includes `speaker` and `timestamp_range`, both nullable, added for finer-grained citation). Pydantic schemas for serialization live in `infrastructure/api/` only — use cases accept/return primitives or domain entities, never Pydantic models.

---

## Skill routing (the core agentic behavior — PRD §6.5)

Three tools, model chooses: `rag_query`, `write_ship30_essay`, `generate_artifact`.

- **Cloud (Anthropic/OpenAI):** native tool-calling is the router. Don't build a separate keyword classifier for these providers.
- **Local (Ollama):** try native tool-calling if the model supports it; if unsupported or the tool-call output is malformed, fall back to a single short LLM call classifying into `RAG | SHIP30 | ARTIFACT | GENERAL`, parsed defensively — **default to `RAG` on any parse failure.** This fallback is a core requirement, not a stretch goal — the mandatory local demo depends on it.

---

## Error handling — required, not optional (PRD §7.1)

| Failure | Required behavior |
|---|---|
| Missing Anthropic/OpenAI API key | Fail fast at startup, name the missing env var. Never fail silently mid-conversation. |
| Ollama unreachable / timeout | Chat-visible error ("Local model didn't respond — is Ollama running?"); configurable timeout, default 30s. |
| DB connection failure | API returns 503 with a clear error body; frontend shows a banner, not a blank chat; in-flight messages aren't silently dropped. |
| Malformed tool-call output (local models) | Caught, routed through the fallback classifier — never surfaced as a raw error. |
| Retrieval returns no relevant chunks | Model says it couldn't find the answer in the transcripts. Never answer from general knowledge. |

Build each of these where the corresponding feature is built, not retrofitted later.

---

## Prompt contracts (PRD §11.5 — keep exact behavior, wording can adapt)

- **RAG:** answer only from retrieved context; if not covered, say "I couldn't find this in Lenny's transcripts."; cite episode (and speaker/timestamp if available); never invent information.
- **Ship30:** ~1250 words, Ship30for30 structure (hook → concrete example → 3-5 bolded lessons → single closing takeaway), grounded only in retrieved context.
- **Artifact:** return only valid Markdown or HTML/CSS inside a single fenced code block, no prose before/after.

---

## Scope boundaries — do not build these

**Non-goals (PRD §2):** authentication/multi-user, billing, image generation, collaborative editing, production-scale deployment.

**Explicit v1→v2 cuts — do not reintroduce unless asked:**
- Chat renaming (new/list/delete is sufficient)
- Monaco Editor (using `react-markdown` + sandboxed iframe instead)
- ChromaDB / second vector store (pgvector only)
- Full mid-stream artifact detection (artifacts render only once a message finishes)

If tempted to add abstraction (DI container, event bus, CQRS, plugin/skill registry) — don't. ARCHITECTURE.md explicitly removed these for a 3-day, 3-skill scope.

---

## Testing expectations (PRD §8 — write alongside the feature, not at the end)

- Provider interface: mock each provider (Anthropic/OpenAI/Ollama).
- Router: test fallback classification logic, including the malformed-output → default-to-RAG path.
- Retrieval: test against a small fixture set of transcript chunks.
- Frontend: 1-2 Playwright smoke tests (send message → response renders; trigger artifact → viewer opens).
- Manual E2E pass: one full run on Anthropic, one on Ollama, covering all three skills plus one deliberate error case.

---

## Working agreements for this repo

1. **Layer check before every change.** State which layer a new file belongs in and confirm its imports only point inward.
2. **No new abstractions without cause.** This is a 3-skill, solo, 3-day build — resist adding registries, containers, or generic frameworks "for future flexibility."
3. **Ports before adapters.** If a use case or skill needs a new capability (new DB query, new provider call), define/extend the interface in `domain/interfaces/` first, then implement it in `infrastructure/`.
4. **Error handling is part of the feature, not a follow-up.** See table above — implement it where it's listed, in the same commit as the feature.
5. **Log failures as you hit them** in `docs/agent-transcripts/` — this is a required deliverable and loses value if reconstructed from memory later.
6. **Check `docs/design.md` for standing decisions** (e.g. embedding model choice) before re-deciding something already settled.
7. **When scope and timeline conflict, cut scope — and document the cut** in `docs/PRD.md`'s cuts table, the same way v1.0→v2.0 cuts were documented.