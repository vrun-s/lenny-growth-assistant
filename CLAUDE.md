# CLAUDE.md

Guidance for Claude Code (and any other agent) working in this repository. This file distills `docs/ARCHITECTURE.md` and `docs/PRD.md` — read those for full detail; this is the operational summary to follow on every change.

It lives at the repo root because that is the only location Claude Code loads automatically. Do not move it into `docs/`.

---

## Project in one paragraph

**Lenny Growth Assistant** — a conversational AI assistant that answers product/growth questions grounded in Lenny's Podcast transcripts (RAG), writes Ship30for30-style essays, and generates Markdown/HTML artifacts. The Claude Agent SDK acts as the **harness** — it owns the agent loop and tool selection. This project extends it with three domain tools, durable Postgres-backed sessions, grounding enforcement, and structured artifact extraction. Solo build, ~3-day timeline, local-first evaluation project — not production infrastructure. **When in doubt, choose the simpler option.**

---

## Non-negotiable architecture rule: dependencies point inward only

```
INFRASTRUCTURE (adapters: API, DB, harness, vectorstore)
        ↓ imports
APPLICATION (use cases, agent skills — plain callables, no SDK import)
        ↓ imports
DOMAIN (entities, port interfaces) — zero framework dependencies
```

- `domain/` never imports FastAPI, SQLAlchemy, Pydantic, Alembic, or **any** provider/agent SDK (`claude_agent_sdk`, `anthropic`, etc.). Entities are plain `dataclasses`, not `BaseModel`/`Base` subclasses.
- `application/` (use cases + skills) only imports `domain/entities/` and `domain/interfaces/`. It must **never** import a concrete class from `infrastructure/` (no repository classes, no harness adapters, no SDK clients, no routers). It talks to the outside world only through the abstract interfaces (ports) declared in `domain/interfaces/`.
- `infrastructure/` implements those ports and is the only place framework code and concrete adapters live — including the Claude Agent SDK and the `anthropic` client.
- `core/` (config, logging) has no dependency on `application/`, `domain/`, or `infrastructure/` — it's pure bootstrapping. Any layer may import from `core/` without creating a cycle.
- Sub-modules inside `infrastructure/` must not import each other directly (e.g. `vectorstore/` must not call `database/` — go through a use case if data needs to cross that boundary).
  - **Documented exception:** `infrastructure/harness/tool_adapters.py` imports skill classes from `application/skills/`. This is an inward dependency (infrastructure → application) and is explicitly permitted; it is the mechanism by which skills become tools.
- `backend/` never imports from `frontend/` or `scripts/`; `frontend/` never imports from `backend/` or `scripts/` (it talks to the API over HTTP/SSE only).
- `scripts/` are thin CLI runners only — no business logic. Ingestion logic lives in `infrastructure/ingestion/`.

**Invariant to enforce:** `grep -r "claude_agent_sdk" backend/app/application backend/app/domain` must return nothing. Treat a hit as a build break.

**Before adding code, ask:** which layer does this belong to, and does it only import from layers below it? If you're about to import a concrete infrastructure class into `application/`, stop — define or reuse a port instead.

---

## Repo layout (follow exactly — see ARCHITECTURE.md §3 for the full tree)

```
CLAUDE.md                this file — must stay at the repo root
docs/                    markdown only, no code
  agent-transcripts/     required deliverable: build log of failures & fixes
deployment/              docker-compose + init SQL, no app code
scripts/                 CLI entrypoints only (run_ingestion.py)
backend/app/
  core/                  config, logging — stdlib + Pydantic only
  domain/
    entities/            Session, Message, Artifact, Document, AgentResult (pure dataclasses)
    interfaces/          repositories.py, agent_harness.py, vectorstore.py (ABCs)
  application/
    use_cases/           create_session, send_message
                         (only where real orchestration exists — see ARCHITECTURE.md §4.6)
    skills/              rag_skill.py, ship30_skill.py, artifact_skill.py
                         (plain callables — no SDK import, no agent loop, no router.py)
  infrastructure/
    api/                 FastAPI routers + deps.py (DI happens here)
    database/            SQLAlchemy models + repositories (only place raw queries live)
    harness/             tool_adapters.py, agent_sdk_harness.py (only place the loop lives)
    vectorstore/         embeddings.py, retriever.py, pgvector_store.py (only place vector ops live)
    ingestion/           parser.py, chunker.py, embedder.py, loader.py
  tests/                 unit/, integration/, conftest.py
frontend/src/
  core/                  api client, constants
  features/{chat,artifacts,settings}/
  shared/                design system components/layouts
```

Deliberately **not present** and not to be reintroduced:
`container.py` / DI framework, `BaseSkill` abstraction, skill registry, `router.py`, `providers/` directory, `BaseProvider` / `AnthropicProvider` / `OpenAIProvider` / `OllamaProvider`, `messages_api_harness.py`, ChromaDB, Monaco Editor.

---

## The harness layer — read before touching `infrastructure/harness/`

**Harness** and **orchestration** are different things. The distinction matters because conflating them was the original architectural error in this project.

- **Harness** = the component that owns the agent loop. It calls the model, receives `tool_use` blocks, executes the corresponding tool, feeds `tool_result` back, and repeats until the model produces a final answer. **Owned by the Claude Agent SDK.** Do not rewrite this.
- **Orchestration** = what each tool actually does (retrieval, prompt assembly, artifact typing), plus session persistence, history rehydration, grounding enforcement, and error mapping. **Owned by this project**, in `application/`.

`infrastructure/harness/` has two files:
- `tool_adapters.py` — wraps each `application/skills/` callable as an SDK-registered tool. Tool *registration* lives here; tool *logic* lives in `application/skills/`.
- `agent_sdk_harness.py` — the single production `IAgentHarness` implementation. Initialises the SDK with registered tools, passes in session history, runs the loop, returns an `AgentResult`.

There is **no second harness adapter** (`messages_api_harness.py` was considered and cancelled — see `docs/design.md`). If the SDK behaves unexpectedly against Ollama, fix the specific config issue; do not write a replacement loop.

---

## Tech stack (don't substitute without a reason written in `docs/design.md`)

- **Frontend:** React + Vite + TypeScript + TailwindCSS v4 + shadcn/ui + `react-markdown` + `rehype-sanitize`; HTML/CSS artifacts render in a sandboxed `<iframe srcDoc>` — never injected into the parent DOM.
- **Backend:** FastAPI + SQLAlchemy + Pydantic + Alembic.
- **Database:** PostgreSQL + pgvector — single database, no second vector store.
- **Agent harness:** `claude-agent-sdk` (Python 3.10+) in `infrastructure/harness/`. Requires Node.js and the Claude Code CLI alongside the Python package — verify and document the exact prerequisites in the README before the evaluator runs it.
- **LLM toggle:** `LLM_PROVIDER=anthropic|ollama`. Resolved in `core/config.py` into a `base_url` + model name — **not** a class selection. Ollama v0.14.0+ exposes an Anthropic-compatible `/v1/messages` endpoint (including tool use), so the same harness and the same tools run against both providers.
  - `LLM_PROVIDER=anthropic` → Anthropic default base URL, `claude-sonnet-*`, `ANTHROPIC_API_KEY` required (fail fast at startup if missing).
  - `LLM_PROVIDER=ollama` → `http://localhost:11434`, model configured separately, dummy API key (required by the client, ignored by Ollama).
  - **OpenAI is not a supported provider.** It was cut in PRD v2.1 — do not add an `OpenAIProvider` or any OpenAI-specific code path.
- **Embeddings:** always `nomic-embed-text` via Ollama locally, regardless of `LLM_PROVIDER`. Using a cloud embeddings API silently breaks the offline requirement. Decided in `docs/design.md` — do not re-litigate.
- **DI:** FastAPI's native `Depends` in `infrastructure/api/deps.py` only. No enterprise container.

---

## Database schema (see PRD §11.3 for full field lists)

`ChatSession`, `Messages` (role, content, optional `artifact_id`), `Artifacts` (type: markdown|html), `Documents` (transcript chunks — includes `speaker` and `timestamp_range`, both nullable, for finer-grained citation).

`AgentResult` is a **domain entity** (plain dataclass): `text`, `citations`, `artifact` (optional). It is the return type of `IAgentHarness.run()`. It keeps SDK message objects out of the inner layers.

Pydantic schemas for serialization live in `infrastructure/api/` only — use cases accept/return primitives or domain entities, never Pydantic models.

All enum columns persist *values* not member names (`user`/`assistant`, `markdown`/`html`) — see `docs/design.md`.

---

## Skill routing — how it actually works now (PRD §6.5)

The model's tool-choice **is** the routing. There is no `router.py` and no keyword classifier.

**Registered tools** (descriptions matter — they are the routing signal):

| Tool | When the model calls it |
|---|---|
| `rag_query` | Any product/growth question answerable from Lenny's transcripts |
| `write_ship30_essay` | Request for a Ship30for30-style essay on a topic |
| `generate_artifact` | Request for a standalone Markdown or HTML/CSS output |

**Cloud (`LLM_PROVIDER=anthropic`):** the SDK calls the tool the model selects. No extra classification step.

**Local (`LLM_PROVIDER=ollama`):** identical flow — Ollama's Anthropic-compatible endpoint supports native tool-calling. Test against your local model on **Day 2 morning**, not Day 3. If a specific compatibility issue surfaces, fix it at the config level and log it in `docs/agent-transcripts/`.

**What this project adds on top of the bare SDK** (the "improve the harness" deliverable):
1. Three domain-specific registered tools with grounding enforcement built into their logic.
2. Durable session state — harness turns persisted to Postgres and rehydrated per turn.
3. Structured artifact extraction from tool output → DB → artifact viewer.
4. Failure mapping into chat-visible user messages rather than SDK stack traces.
5. Portability across cloud and local via one env var.

---

## Error handling — required, not optional (PRD §7.1)

| Failure | Required behavior |
|---|---|
| Missing `ANTHROPIC_API_KEY` when `LLM_PROVIDER=anthropic` | Fail fast at startup, name the missing env var. Never fail silently mid-conversation. |
| Ollama unreachable / timeout | Chat-visible error ("Local model didn't respond — is Ollama running?"); configurable timeout, default 30s. |
| DB connection failure | API returns 503 with a clear error body; frontend shows a banner, not a blank chat; in-flight messages aren't silently dropped. |
| Tool raises / returns malformed output | Caught in `tool_adapters.py`, returned to the loop as a `tool_result` error so the model can recover; iteration cap prevents runaway loops. |
| Retrieval returns no relevant chunks | Tool returns empty context; model says it couldn't find the answer in the transcripts. Never answer from general knowledge. |

Build each of these where the corresponding feature is built, not retrofitted later.

---

## Prompt contracts (PRD §11.5 — keep exact behavior, wording can adapt)

- **System prompt (harness-level):** you are a growth advisor grounded in Lenny's transcripts; use the provided tools; never answer product/growth questions from your own knowledge.
- **RAG tool:** answer only from retrieved context; if not covered, say "I couldn't find this in Lenny's transcripts."; cite episode (and speaker/timestamp if available); never invent information.
- **Ship30 tool:** ~1250 words, Ship30for30 structure (hook → concrete example → 3-5 bolded lessons → single closing takeaway), grounded only in retrieved context.
- **Artifact tool:** return only valid Markdown or HTML/CSS as structured tool output with an explicit type field (`"markdown"` or `"html"`); no prose before/after.

---

## Scope boundaries — do not build these

*This is the canonical list. `docs/ARCHITECTURE.md` and `docs/workflow.md` point here rather than restating it — if something changes, change it here only.*

**Non-goals (PRD §2):** authentication/multi-user, billing, image generation, collaborative editing, production-scale deployment.

**Cancelled in v2.1 — do not reintroduce:**
- `application/skills/router.py` (the model is the router)
- `infrastructure/providers/` and the `BaseProvider → Anthropic/OpenAI/Ollama` class hierarchy (replaced by config rows)
- `infrastructure/harness/messages_api_harness.py` (second loop, over-engineering — see `docs/design.md`)
- OpenAI as a provider (cut to simplify; cloud path is Anthropic only)
- Fallback keyword classifier for local models (Ollama supports native tool-calling)

**Explicit v1→v2 cuts — do not reintroduce unless asked:**
- Chat renaming (new/list/delete is sufficient)
- Monaco Editor (using `react-markdown` + sandboxed iframe instead)
- ChromaDB / second vector store (pgvector only)
- Full mid-stream artifact detection (artifacts render only once a message finishes)

If tempted to add abstraction (DI container, event bus, CQRS, plugin/skill registry, `BaseSkill`) — don't. ARCHITECTURE.md explicitly removed these for a 3-day, 3-skill scope. The same test applies to use cases: a class that only forwards one call to one repository is indirection, not architecture (ARCHITECTURE.md §4.6).

---

## Testing expectations (PRD §8 — write alongside the feature, not at the end)

- **Skill bodies (unit):** the three skills are plain callables with no SDK dependency — test them directly with a mock `IVectorStore` and a small fixture set of transcript chunks. This is the main payoff of keeping tool logic in `application/`.
- **Harness port (unit):** `SendMessageUseCase` is tested against a mock `IAgentHarness` — no network, no SDK.
- **Tool error handling (unit):** verify that a tool exception is returned as a `tool_result` error rather than propagating up.
- **API (integration):** session CRUD endpoints and one chat round-trip with a stubbed harness.
- **Frontend:** 1-2 Playwright smoke tests (send message → response renders; trigger artifact → viewer opens).
- **Manual E2E:** one full run on Anthropic, one on Ollama, covering all three tools plus one deliberate error case (e.g. stop Ollama mid-conversation). Log results in `docs/agent-transcripts/`.

---

## Working agreements for this repo

1. **Layer check before every change.** State which layer a new file belongs in and confirm its imports only point inward.
2. **Harness rule.** If you find yourself writing an agent loop (call model → check tool_use → call tool → feed result back → repeat) anywhere outside `infrastructure/harness/`, stop. That is the SDK's job.
3. **No new abstractions without cause.** This is a 3-skill, solo, 3-day build — resist adding registries, containers, or generic frameworks "for future flexibility."
4. **Ports before adapters.** If a use case or skill needs a new capability (new DB query, new harness call), define/extend the interface in `domain/interfaces/` first, then implement it in `infrastructure/`.
5. **Error handling is part of the feature, not a follow-up.** See table above — implement it in the same commit as the feature.
6. **Log failures as you hit them** in `docs/agent-transcripts/build-log.md` — this is a required deliverable and loses value if reconstructed from memory later.
7. **Check `docs/design.md` for standing decisions** (embedding model, enum strategy, API prefix, use-case policy) before re-deciding something already settled.
8. **When scope and timeline conflict, cut scope — and document the cut** in `docs/PRD.md`'s cuts table, the same way v1.0→v2.0 and v2.0→v2.1 cuts were documented.
9. **Track progress in `docs/workflow.md`** — it is the single phase plan and checklist. Keep its checkboxes current; there is no second copy to sync.