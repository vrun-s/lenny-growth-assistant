# Architecture Contract: Clean Architecture Dependency Rules

This document establishes the architectural boundaries and dependency rules for the **Lenny Growth Assistant** project. All developers, agents, and automated code generation tools (including Claude Code) MUST strictly adhere to these rules.

---

## 0. Harness vs. Orchestration (read this first)

These two words are used precisely throughout this document, because conflating them was the original architectural error.

* **Harness** — the component that owns the *agent loop*: it calls the model, receives `tool_use` blocks, executes the corresponding tool, feeds the result back, and repeats until the model produces a final answer. It also owns per-turn context assembly and tool-call error recovery.
  **This project does not write a harness. It adopts one: the Claude Agent SDK.**
* **Orchestration** — this project's own business logic: what `rag_query`, `write_ship30_essay`, and `generate_artifact` actually *do* (retrieval, prompt assembly, grounding rules, artifact typing), plus session persistence, history loading, and error mapping.
  **This project owns all of it**, and it lives in `application/`.

The rule that follows from the distinction:

> The harness runs the loop. The application layer supplies the tools the loop calls, and the persistence around it. Neither implements the other.

An earlier revision of this document specified `application/skills/router.py` — a hand-written class that inspected tool-call output and dispatched to skills. That is a harness, written from scratch, in the wrong layer. It has been removed.

---

## 1. Clean Architecture Dependency Boundaries

Dependencies MUST only point inwards. Outer layers (Frameworks and Adapters) can depend on inner layers (Use Cases and Domain), but inner layers MUST NOT depend on outer layers.

```
       ┌──────────────────────────────────────────────────────────┐
       │                 INFRASTRUCTURE (Adapters)                │
       │   API · DB Repositories · Vector Store · Agent Harness   │
       │        (Claude Agent SDK + tool registration)            │
       └────────────────────────────┬─────────────────────────────┘
                                    │ imports
                                    ▼
       ┌──────────────────────────────────────────────────────────┐
       │        APPLICATION (Use Cases & Agent Skills)            │
       │   SendMessage · RAGSkill · Ship30Skill · ArtifactSkill   │
       │              (skill logic — NO agent loop)               │
       └────────────────────────────┬─────────────────────────────┘
                                    │ imports
                                    ▼
       ┌──────────────────────────────────────────────────────────┐
       │        DOMAIN (Core Entities & Port Interfaces)          │
       │  Session entity · IRepository · IAgentHarness · IVectorStore │
       └──────────────────────────────────────────────────────────┘
```

Note the direction of the harness relationship: infrastructure **registers** application skills as tools with the SDK. The application layer never imports `claude_agent_sdk`.

---

## 2. Directory Dependency Rules

### 2.1 Top-Level Folders

#### `docs/`
* **Responsibility:** Houses markdown specifications, designs, transcripts, and system architecture plans.
* **Allowed Dependencies:** None.
* **Forbidden Dependencies:** Must not contain source code, imports, or executable scripts.

#### `deployment/`
* **Responsibility:** Contains the local runtime orchestration (`docker-compose.yml` for Postgres + pgvector) and its init scripts. Production images are out of scope — PRD §2 lists production-scale deployment as a non-goal.
* **Allowed Dependencies:** Internal configuration templates.
* **Forbidden Dependencies:** Must not contain application source code or run imports.

#### `scripts/`
* **Responsibility:** Dedicated CLI entrypoints for administrative and operational tasks (e.g. launching ingestion).
* **Allowed Dependencies:** `backend/app/core/`, `backend/app/infrastructure/`, `backend/app/application/`, and `backend/app/domain/`.
* **Forbidden Dependencies:** Must not contain core business algorithms or raw parser logic (all ingestion details belong in the infrastructure layer).

#### `backend/`
* **Responsibility:** Enforces Clean Architecture layers, containing the API application, harness integration, business use cases, entity models, and tests.
* **Allowed Dependencies:** Internal layer communication adhering to Section 1 & Section 2.2 rules.
* **Forbidden Dependencies:** Must never import code from `frontend/` or `scripts/`.

#### `frontend/`
* **Responsibility:** Houses UI pages, components, client-side state hooks, and API service wrappers for the React SPA.
* **Allowed Dependencies:** Consumes HTTP/SSE boundaries exposed by the API layer.
* **Forbidden Dependencies:** Must not import code or types from `backend/` or `scripts/` directly.

---

### 2.2 Backend Architectural Sub-folders

#### `backend/app/core/`
* **Responsibility:** Manages global application boot processes, environment configuration parameters, and central logging.
* **Allowed Dependencies:** Standard Python library, environment configurations, and Pydantic.
* **Forbidden Dependencies:** Must not depend on or import from `application/`, `domain/`, or `infrastructure/` packages.
* **Note:** `core/` is a dependency-free shared kernel — because it imports nothing from the other layers, **any** layer may import *from* it without creating a cycle.

#### `backend/app/domain/`
* **Responsibility:** Represents core business concepts (Entities) and boundaries (Ports). It has **zero dependencies** on third-party frameworks.
* **Allowed Dependencies:** Standard Python library (e.g., `dataclasses`, `typing`, `uuid`).
* **Forbidden Dependencies:** Must NEVER import from `application/`, `infrastructure/`, `core/`, or external frameworks (FastAPI, SQLAlchemy, Pydantic, **or `claude_agent_sdk`**).

#### `backend/app/application/`
* **Responsibility:** Defines specific application logic flows (Use Cases) and the callable bodies of the three agent skills.
* **Allowed Dependencies:** `domain/entities/` and `domain/interfaces/`.
* **Forbidden Dependencies:** Must never import from concrete components inside `infrastructure/` (repositories, harness adapters, SDK clients, API routers). **In particular, must never import `claude_agent_sdk` or implement an agent loop** — see §4.7.

#### `backend/app/infrastructure/`
* **Responsibility:** Implements ports and interacts with external frameworks, APIs, databases, vector stores, parsing pipelines, and the agent harness.
* **Allowed Dependencies:** `domain/`, `application/`, and framework libraries (SQLAlchemy, FastAPI, `claude_agent_sdk`, `anthropic`).
* **Forbidden Dependencies:** Sub-modules under infrastructure (e.g. `database`, `harness`, `vectorstore`) must not import from one another directly.
  * **Documented exception:** `harness/tool_adapters.py` imports the skill classes from `application/skills/`. This is an inward dependency (infrastructure → application) and is explicitly permitted; it is the mechanism by which skills become tools.

---

## 3. Visual Repository Tree

Files marked *(planned)* do not exist yet and are listed to fix their eventual location, not to imply they are built.

```text
lenny-growth-assistant/
├── CLAUDE.md                              # Agent operating rules (must sit at the repo root to load)
├── docs/                                  # Project documentation & contracts
│   ├── PRD.md
│   ├── ARCHITECTURE.md
│   ├── design.md
│   ├── workflow.md                        # Phased build plan + checklist
│   └── agent-transcripts/                 # Required deliverable: build log of failures & fixes
├── deployment/                            # Local runtime orchestration
│   ├── docker-compose.yml                 # Postgres + pgvector
│   └── init/enable-pgvector.sql           # CREATE EXTENSION, run on first container start
├── scripts/                               # CLI entrypoints (Contains ONLY runners, NO business logic)
│   └── run_ingestion.py                   # Ingestion pipeline runner CLI
├── backend/                               # Python Clean Architecture backend root
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                        # FastAPI startup entry and bootstrapping definitions
│   │   │
│   │   ├── core/                          # System Configuration & Bootstrapping
│   │   │   ├── config.py                  # Pydantic env config (incl. harness base_url/model resolution)
│   │   │   └── logging.py                 # Central logger initialization
│   │   │
│   │   ├── domain/                        # Layer 1: Core Domain Rules (Purity Layer)
│   │   │   ├── entities/                  # Pure python dataclasses representing core entities
│   │   │   │   ├── session.py
│   │   │   │   ├── message.py
│   │   │   │   ├── artifact.py
│   │   │   │   ├── document.py
│   │   │   │   └── agent_result.py        # Harness return type: text + citations + optional artifact
│   │   │   └── interfaces/                # Declared ports (Abstract Base Classes)
│   │   │       ├── repositories.py        # CRUD database repository contracts
│   │   │       ├── agent_harness.py       # IAgentHarness — replaces the old ILLMProvider port
│   │   │       └── vectorstore.py         # Vector Index Adapter contract
│   │   │
│   │   ├── application/                   # Layer 2: Business Use Cases & Skill Logic
│   │   │   ├── use_cases/
│   │   │   │   ├── create_session.py
│   │   │   │   └── send_message.py        # (planned) load history → IAgentHarness.run() → persist
│   │   │   └── skills/                    # Skill BODIES only — plain callables, no SDK import
│   │   │       ├── rag_skill.py           # Retrieve via IVectorStore → grounded context + citations
│   │   │       ├── ship30_skill.py        # Retrieve + assemble the Ship30 essay prompt/structure
│   │   │       └── artifact_skill.py      # Produce typed artifact payload (markdown | html)
│   │   │
│   │   └── infrastructure/                # Layer 3: Details & Adapters
│   │       ├── api/                       # API HTTP delivery layer (FastAPI endpoints)
│   │       │   ├── v1/
│   │       │   │   ├── session_router.py
│   │       │   │   ├── schemas.py         # Pydantic request/response models
│   │       │   │   ├── chat_router.py     # (planned)
│   │       │   │   └── artifact_router.py # (planned)
│   │       │   ├── deps.py                # FastAPI dependency injection definitions
│   │       │   └── app.py                 # FastAPI application mount
│   │       ├── database/                  # SQL database engine, models & repositories
│   │       │   ├── connection.py          # Lazily-built engine + session factory
│   │       │   ├── orm_models.py          # SQLAlchemy models mapping database tables
│   │       │   └── repositories/
│   │       │       ├── session_repo.py
│   │       │       └── message_repo.py
│   │       ├── harness/                   # THE AGENT LOOP LIVES HERE — nowhere else
│   │       │   ├── tool_adapters.py       # Wraps application skills as SDK tools
│   │       │   └── agent_sdk_harness.py   # Claude Agent SDK owns the loop (see §6)
│   │       ├── vectorstore/
│   │       │   ├── embeddings.py          # nomic-embed-text via Ollama (see design.md — unchanged)
│   │       │   ├── retriever.py           # Document retrieval & citation logic adapter
│   │       │   └── pgvector_store.py      # pgvector storage driver client
│   │       └── ingestion/
│   │           ├── parser.py
│   │           ├── chunker.py
│   │           ├── embedder.py
│   │           └── loader.py
│   │
│   ├── tests/
│   │   ├── conftest.py                    # Mock fixtures definitions
│   │   ├── unit/                          # Skill bodies + use case logic
│   │   └── integration/                   # Router/API integration tests
│   │
│   ├── alembic/
│   ├── alembic.ini
│   ├── requirements.txt
│   └── requirements-dev.txt
└── frontend/                              # Frontend React app workspace root
    └── src/
        ├── main.tsx
        ├── App.tsx
        ├── core/                          # Global setups & base HTTP/SSE clients
        │   ├── api_client.ts
        │   └── constants.ts
        ├── features/
        │   ├── chat/
        │   ├── artifacts/
        │   └── settings/
        └── shared/
            ├── components/
            ├── layouts/
            └── index.css
```

---

## 4. Architectural Rules (The Contract)

### 4.1 Domain Purity
* Files in `domain/` must remain pure Python. No FastAPI, SQLAlchemy, Alembic, or agent/model SDKs.
* Domain entities must be standard `dataclasses` or normal classes. They must not inherit from SQLAlchemy's `Base` or Pydantic's `BaseModel`.

### 4.2 Dependency Inversion (Ports & Adapters)
* High-level business logic must never instantiate concrete low-level implementation details.
* Use Cases interact with the database, the agent harness, and the vector index *strictly* through abstract Interface declarations (Ports).

### 4.3 Database & Vector Query Isolation
* Direct database queries or ORM models must never appear outside `infrastructure/database/`.
* Direct vector calculations or pgvector-specific operators must never appear outside `infrastructure/vectorstore/`.

### 4.4 Request & Response Serialization Boundary
* Pydantic schemas reside inside `infrastructure/api/`. They represent serialization formats for network endpoints.
* Use cases receive primitives or Domain Entities and return Domain Entities.
* Response models map from domain entities via `ConfigDict(from_attributes=True)` + `model_validate()`. Do not hand-write field-by-field `from_entity()` mappers.

### 4.5 Dependency Injection (DI) Rule
* Class dependencies are declared in `__init__` using type hints referencing abstract Interfaces (Ports).
* Concrete implementations are resolved at request time via FastAPI's `Depends` in `infrastructure/api/deps.py`.
* Heavy enterprise container registries are forbidden.

### 4.6 Use Cases Must Earn Their Layer
* A use case exists to hold orchestration that belongs to neither the router nor the repository — generating identity and timestamps, coordinating multiple ports, enforcing an invariant.
* A class whose `execute()` only forwards its arguments to a single repository method is **not** a use case; it is indirection. Routers may call a repository port directly for such operations — the dependency still points inward.
* Add the use case when the logic arrives, not in anticipation of it.
* `SendMessageUseCase` earns its layer: it loads history, invokes `IAgentHarness`, persists the assistant message, and links any produced artifact — four coordinated steps across three ports.

### 4.7 The Harness Owns the Loop (new)
* **No agent loop may be written in `application/` or `domain/`.** There is exactly one loop, and it is supplied by the Claude Agent SDK inside `infrastructure/harness/`.
* Skills in `application/skills/` are **plain callables**. They take typed arguments, do retrieval and prompt assembly, and return a result. They do not decide when they are called, do not inspect `tool_use` blocks, and do not call the model to choose among themselves.
* Tool *registration* (SDK decorators, JSON schemas, MCP server construction) lives in `infrastructure/harness/tool_adapters.py`. Tool *logic* lives in `application/skills/`. This split is what keeps the SDK out of the business layer while still letting the SDK drive.
* `grep -r "claude_agent_sdk" backend/app/application backend/app/domain` must return nothing. Treat a hit as a build break.

### 4.8 One Toggle, One Harness Interface
* `IAgentHarness` is the single port through which any use case reaches a model. There is no per-vendor provider class.
* Switching between cloud and local changes **configuration** (base URL + model name), not the class graph — see §5.

---

## 5. The LLM Toggle

`LLM_PROVIDER` remains the single user-facing switch required by PRD §6.3. `core/config.py` resolves it into a base URL and model name:

| `LLM_PROVIDER` | Base URL | Model | Auth |
|---|---|---|---|
| `anthropic` | Anthropic default | `claude-sonnet-*` | `ANTHROPIC_API_KEY` (required; fail fast at startup) |
| `ollama` | `http://localhost:11434` | e.g. `qwen3-coder` | dummy key — required by the client, ignored by Ollama |

This works because Ollama (v0.14.0+) exposes an **Anthropic-compatible `/v1/messages` endpoint**, including tool use. The evaluator's guidance — *"claude sdk allows using any LLM as the underlying model, as long as they support anthropic-like endpoints"* — is exactly this mechanism.

Consequences worth stating plainly:

* The old `BaseProvider → AnthropicProvider | OpenAIProvider | OllamaProvider` hierarchy is **deleted**. Three adapter classes collapse into two config rows.
* **OpenAI is dropped.** The brief requires "a cloud provider (e.g. Anthropic Claude, OpenAI)" — one satisfies it, and the brief separately mandates building on the Claude SDK. A third provider is scope this project did not need.
* Embeddings are unaffected: `nomic-embed-text` via Ollama, always, per `design.md`. The offline guarantee holds because both chat and embeddings resolve to localhost when `LLM_PROVIDER=ollama`.

---

## 6. The Single Harness Adapter

`IAgentHarness` has exactly one production implementation: `agent_sdk_harness.py`.

It wraps the Claude Agent SDK. The SDK owns the loop, tool execution, and per-turn context. Both `LLM_PROVIDER=anthropic` and `LLM_PROVIDER=ollama` go through it — they differ only in `base_url` and model name (see §5).

**There is no fallback harness.** An earlier revision of this document specified a second `messages_api_harness.py` as a thin loop over the raw Messages API in case the SDK misbehaved against Ollama. That was over-engineering in response to uncertainty: Ollama v0.14.0+ exposes a documented, tested Anthropic-compatible `/v1/messages` endpoint including tool use, and the risk was based on reports about the Claude Code *CLI* — not the Agent SDK used programmatically with controlled feature flags. A second loop is real Day 2 time spent on a contingency that probably never fires.

**How to handle an actual incompatibility:** test the harness against Ollama first thing on Day 2. If a specific SDK feature hits an unsupported sub-endpoint, the fix is a config flag or disabling that one feature — not a second implementation. Record whatever happens in `docs/agent-transcripts/`; the attempt and its outcome are a required deliverable regardless.

`IAgentHarness` still earns its place as the port you mock in unit tests, keeping `SendMessageUseCase` testable without the SDK.

---

## 7. What "Improving the Harness" Means Here

The brief (as clarified) asks for a harness that is *used and improved*, not merely imported. The improvements this project layers on top of the Claude Agent SDK, all of which are ours:

* **Three domain-specific tools** — `rag_query`, `write_ship30_essay`, `generate_artifact` — registered as in-process SDK tools, so tool *choice* is the model's and tool *behaviour* is ours.
* **Durable session state.** The SDK's session handling is process-local; PRD §7 requires sessions to survive a backend restart. `SendMessageUseCase` bridges harness turns to Postgres-backed `ChatSession` / `Messages`, and rehydrates history on the next turn.
* **Grounding enforcement.** The RAG tool returns retrieved context plus citations, and the system prompt forbids answering outside it — the "decline rather than guess" behaviour in PRD §6.4 is enforced at the tool boundary, not left to the model.
* **Structured artifact extraction.** Artifact type (`markdown` | `html`) comes from the tool's structured output, is persisted, and is linked to the message — never scraped from chat text (PRD §6.6).
* **Failure mapping.** Missing key, local-model timeout, and DB failure are translated into the chat-visible behaviours in PRD §7.1 rather than surfacing as SDK stack traces.
* **Provider portability.** The same tool set runs against both a cloud Claude model and a local Ollama model behind one env var.

---

## 8. Placement Decisions

Four placements are non-obvious enough to record; the rest follow from §1–§4.

**The agent loop lives in `infrastructure/harness/`, not `application/`.** The loop is a technical mechanism supplied by an external SDK — the same category as a database driver. Putting it in `application/` (as the deleted `router.py` did) meant the business layer depended on an SDK's control flow and had to be re-tested through it.

**Tool logic lives in `application/skills/`; tool registration lives in `infrastructure/harness/tool_adapters.py`.** Splitting them is what allows the SDK to drive the loop while the business layer stays SDK-free and unit-testable as ordinary functions.

**Vector operations live in `infrastructure/vectorstore/`.** Embedding generation and pgvector operators are technical details. The RAG skill depends on the `IVectorStore` port, so swapping pgvector touches only infrastructure.

**Ingestion logic lives in `infrastructure/ingestion/`, not `scripts/`.** Parsing, chunking, embedding, and loading are testable and reusable from the server; `scripts/run_ingestion.py` stays a thin CLI wrapper with zero processing logic.

For the list of abstractions deliberately **not** built (DI container, `BaseSkill`, skill registry, second vector store, per-vendor provider classes), see the canonical list in `CLAUDE.md` → "Scope boundaries". It is not repeated here.

---

## 9. Runtime Prerequisite (README must state this)

The Python Claude Agent SDK is a wrapper around the Claude Code runtime and therefore expects **Node.js** and the Claude Code CLI to be present in addition to `pip install claude-agent-sdk` (Python 3.10+). Verify the exact current requirement against the official Agent SDK documentation before finalising the README — an evaluator hitting an undocumented Node dependency on first run is a preventable failure, and it is the single most likely reason a working build looks broken on someone else's laptop.