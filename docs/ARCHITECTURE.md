# Architecture Contract: Clean Architecture Dependency Rules

This document establishes the architectural boundaries and dependency rules for the **Lenny Growth Assistant** project. All developers, agents, and automated code generation tools (including Claude Code) MUST strictly adhere to these rules.

---

## 1. Clean Architecture Dependency Boundaries

The architecture organizes the codebase into concentric layers where dependencies MUST only point inwards. Outer layers (Frameworks and Adapters) can depend on inner layers (Use Cases and Domain), but inner layers MUST NOT depend on outer layers.

```
       ┌──────────────────────────────────────────────────────────┐
       │                 INFRASTRUCTURE (Adapters)                │
       │     (API, DB Repositories, Providers, Vector Store)      │
       └────────────────────────────┬─────────────────────────────┘
                                    │ imports
                                    ▼
       ┌──────────────────────────────────────────────────────────┐
       │         APPLICATION (Use Cases & Agent Skills)           │
       │     (SendMessage, WriteShip30, RAGSkill, Router)         │
       └────────────────────────────┬─────────────────────────────┘
                                    │ imports
                                    ▼
       ┌──────────────────────────────────────────────────────────┐
       │         DOMAIN (Core Entities & Port Interfaces)          │
       │    (Session entity, IRepository port, IProvider port)    │
       └──────────────────────────────────────────────────────────┘
```

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
* **Responsibility:** Enforces Clean Architecture layers, containing the API application, core engines, business use cases, entity models, and tests.
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
* **Forbidden Dependencies:** Must NEVER import from `application/`, `infrastructure/`, `core/`, or external frameworks (such as FastAPI, SQLAlchemy, or Pydantic).

#### `backend/app/application/`
* **Responsibility:** Defines specific application logic flows (Use Cases) and orchestrates LLM tools (Agent Skills).
* **Allowed Dependencies:** `domain/entities/` and `domain/interfaces/`.
* **Forbidden Dependencies:** Must never import from concrete components inside `infrastructure/` (e.g. repositories, specific provider SDK clients, or API routers).

#### `backend/app/infrastructure/`
* **Responsibility:** Implements interfaces (ports) and interacts with external frameworks, APIs, databases, vector stores, and parsing pipelines.
* **Allowed Dependencies:** `domain/`, `application/`, and framework libraries (SQLAlchemy, FastAPI, Anthropic SDK).
* **Forbidden Dependencies:** Sub-modules under infrastructure (e.g. database, providers, vectorstore) must not import from one another directly (e.g., the vector store must not call the database repository).

---

## 3. Visual Repository Tree

This tree represents the target folder structure that tools, developer agents, and humans must follow when introducing code changes. Files marked *(planned)* do not exist yet and are listed to fix their eventual location, not to imply they are built:

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
│   │   │   ├── config.py                  # Pydantic environment configurations
│   │   │   └── logging.py                 # Central logger initialization
│   │   │
│   │   ├── domain/                        # Layer 1: Core Domain Rules (Purity Layer)
│   │   │   ├── entities/                  # Pure python dataclasses representing core entities
│   │   │   │   ├── session.py
│   │   │   │   ├── message.py
│   │   │   │   ├── artifact.py
│   │   │   │   └── document.py
│   │   │   └── interfaces/                # Declared ports (Abstract Base Classes)
│   │   │       ├── repositories.py        # CRUD database repository contracts
│   │   │       ├── llm_provider.py        # LLM Engine Adapter contract
│   │   │       └── vectorstore.py         # Vector Index Adapter contract
│   │   │
│   │   ├── application/                   # Layer 2: Business Use Cases & Skills Orchestration
│   │   │   ├── use_cases/                 # Orchestrators that carry real logic (see §4.6)
│   │   │   │   ├── create_session.py
│   │   │   │   ├── send_message.py        # (planned)
│   │   │   │   ├── write_ship30.py        # (planned)
│   │   │   │   └── generate_artifact.py   # (planned)
│   │   │   └── skills/                    # Isolated AI Agent Skills (Directly orchestrated by the Router)
│   │   │       ├── rag_skill.py           # Knowledge base query workflow
│   │   │       ├── ship30_skill.py        # Essay structure compiler workflow
│   │   │       ├── artifact_skill.py      # Code generation output builder
│   │   │       └── router.py              # Skill classification and tool router
│   │   │
│   │   └── infrastructure/                # Layer 3: Details & Adapters (Concrete Details)
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
│   │       │   └── repositories/          # Concrete adapters writing to PostgreSQL
│   │       │       ├── session_repo.py
│   │       │       └── message_repo.py
│   │       ├── providers/                 # LLM Client Adapters
│   │       │   ├── anthropic_provider.py  # Anthropic Claude Adapter
│   │       │   ├── openai_provider.py     # OpenAI GPT-4o Adapter
│   │       │   └── ollama_provider.py     # Local Ollama Adapter
│   │       ├── vectorstore/               # Vector storage and retrieval adapters
│   │       │   ├── embeddings.py          # Embeddings generator client
│   │       │   ├── retriever.py           # Document retrieval & citation logic adapter
│   │       │   └── pgvector_store.py      # pgvector storage driver client
│   │       └── ingestion/                 # Concrete document processing modules
│   │           ├── parser.py              # Transcript documents parser
│   │           ├── chunker.py             # Splitting chunk algorithms
│   │           ├── embedder.py            # Embedding vectors calculator
│   │           └── loader.py              # SQL Vector database loader
│   │
│   ├── tests/                             # Python Test Suites
│   │   ├── conftest.py                    # Mock fixtures definitions
│   │   ├── unit/                          # Isolated business logic unit tests
│   │   └── integration/                   # Controllers integration tests
│   │
│   ├── alembic/                           # Migration environment & versions
│   ├── alembic.ini
│   ├── requirements.txt                   # Runtime dependencies (pinned)
│   └── requirements-dev.txt               # Adds pytest + httpx for the test suite
└── frontend/                              # Frontend React app workspace root
    ├── src/
    │   ├── main.tsx
    │   ├── App.tsx
    │   ├── core/                          # Global setups & base HTTP/SSE clients
    │   │   ├── api_client.ts
    │   │   └── constants.ts
    │   ├── features/                      # Feature modules folders
    │   │   ├── chat/                      # Chat window interfaces & chat hooks
    │   │   │   ├── components/
    │   │   │   ├── hooks/
    │   │   │   └── types.ts
    │   │   ├── artifacts/                 # Side pane previews & iframe layouts
    │   │   │   ├── components/
    │   │   │   ├── hooks/
    │   │   │   └── types.ts
    │   │   └── settings/                  # Settings page & toggles layouts
    │   │       ├── components/
    │   │       └── types.ts
    │   └── shared/                        # App shared layouts & components
    │       ├── components/                # Design elements (Buttons, Inputs)
    │       ├── layouts/                   # Shared flex layouts
    │       └── index.css                  # Main layout styling rules
```

---

## 4. Architectural Rules (The Contract)

### 4.1 Domain Purity
* Files in `domain/` must remain pure Python files. They must not import FastAPI, SQLAlchemy, Alembic, or any model SDKs.
* Domain entities must be standard Python `dataclasses` or normal classes. They must not inherit from SQLAlchemy's `Base` or Pydantic's `BaseModel`.

### 4.2 Dependency Inversion (Ports & Adapters)
* High-level business logic must never instantiate concrete low-level implementation details.
* Use Cases and Skills must interact with databases, LLM engines, and vector indexes *strictly* through abstract Interface declarations (Ports).

### 4.3 Database & Vector Query Isolation
* Direct database queries or ORM models must never appear outside the `infrastructure/database/` directory.
* Direct vector calculations or vector-store specific queries (e.g. pgvector operator definitions) must never appear outside the `infrastructure/vectorstore/` directory.

### 4.4 Request & Response Serialization Boundary
* Pydantic schemas reside inside the `infrastructure/api/` layer or separate schema models. They represent serialization formats for network endpoints.
* Use cases receive parameters as primitive types or Domain Entities and return Domain Entities.
* Response models map from domain entities via `ConfigDict(from_attributes=True)` + `model_validate()`. Do not hand-write field-by-field `from_entity()` mappers.

### 4.5 Dependency Injection (DI) Rule
* Class dependencies must be declared in constructors (`__init__`) using type hints referencing abstract Interfaces (Ports).
* Concrete implementations are resolved and bound dynamically at request time using FastAPI's built-in dependency injection system via `Depends` in `backend/app/infrastructure/api/deps.py`.
* Heavy enterprise container registries are forbidden.

### 4.6 Use Cases Must Earn Their Layer
* A use case exists to hold orchestration that belongs to neither the router nor the repository — generating identity and timestamps, coordinating multiple ports, enforcing an invariant.
* A class whose `execute()` only forwards its arguments to a single repository method is **not** a use case; it is indirection. Routers may call a repository port directly for such operations — the dependency still points inward, since routers depend on `domain/interfaces/`, never on a concrete repository class.
* Add the use case when the logic arrives, not in anticipation of it.

---

## 5. Placement Decisions

Three placements are non-obvious enough to record; the rest follow from §1–§4.

**Skills live in `application/`, not `infrastructure/`.** RAG, essay writing, and artifact generation are business capabilities, not technical adapters. Placing them beside use cases keeps them unit-testable without network stubs — they reach the outside world only through `ILLMProvider` and `IVectorStore`.

**Vector operations live in `infrastructure/vectorstore/`.** Embedding generation and pgvector operators are technical details. The RAG skill depends on the `IVectorStore` port, so swapping pgvector for another store touches only the infrastructure layer.

**Ingestion logic lives in `infrastructure/ingestion/`, not in `scripts/`.** Parsing, chunking, embedding, and loading are testable and reusable from the server; `scripts/run_ingestion.py` stays a thin CLI wrapper with zero processing logic.

For the list of abstractions deliberately **not** built (DI container, `BaseSkill`, skill registry, second vector store), see the single canonical list in `CLAUDE.md` → "Scope boundaries". It is not repeated here.