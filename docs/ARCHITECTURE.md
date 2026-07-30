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
* **Responsibility:** Contains DevOps configurations, Dockerfiles, and orchestration manifests (e.g. docker-compose, Kubernetes specs) for runtime environments.
* **Allowed Dependencies:** Internal configuration templates.
* **Forbidden Dependencies:** Must not contain application source code or run imports.

#### `scripts/`
* **Responsibility:** Dedicated CLI entrypoints for administrative and operational tasks (e.g. launching ingestion, seeding databases).
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
* **Responsibility:** Manages global application boot processes, environment configuration parameters, central logging, and system-wide constants.
* **Allowed Dependencies:** Standard Python library, environment configurations, and Pydantic.
* **Forbidden Dependencies:** Must not depend on or import from `application/`, `domain/`, or `infrastructure/` packages.

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

This tree represents the final folder structure that tools, developer agents, and humans must follow when introducing code changes:

```text
lenny-growth-assistant/
├── docs/                                  # Project documentation & contracts
│   ├── PRD.md
│   ├── ARCHITECTURE.md
│   └── design.md
├── deployment/                            # DevOps, staging configurations, and Docker assets
│   ├── docker-compose.yml                 # Local environments orchestrator
│   ├── Dockerfile.backend                 # Multi-stage image build for Python/FastAPI
│   └── Dockerfile.frontend                # Multi-stage image build for React static assets
├── scripts/                               # CLI entrypoints (Contains ONLY runners, NO business logic)
│   ├── run_ingestion.py                   # Ingestion pipeline runner CLI
│   └── seed_database.py                   # Dev sandbox database seeder CLI
├── backend/                               # Python Clean Architecture backend root
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                        # FastAPI startup entry and bootstrapping definitions
│   │   │
│   │   ├── core/                          # System Configuration & Bootstrapping
│   │   │   ├── config.py                  # Pydantic environment configurations
│   │   │   ├── logging.py                 # Central logger initialization
│   │   │   └── constants.py               # Global system constants & errors
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
│   │   │   ├── use_cases/                 # Single-responsibility orchestrators (Use Cases)
│   │   │   │   ├── create_session.py
│   │   │   │   ├── send_message.py
│   │   │   │   ├── write_ship30.py
│   │   │   │   └── generate_artifact.py
│   │   │   └── skills/                    # Isolated AI Agent Skills (Directly orchestrated by the Router)
│   │   │       ├── rag_skill.py           # Knowledge base query workflow
│   │   │       ├── ship30_skill.py        # Essay structure compiler workflow
│   │   │       ├── artifact_skill.py      # Code generation output builder
│   │   │       └── router.py              # Skill classification and tool router
│   │   │
│   │   └── infrastructure/                # Layer 3: Details & Adapters (Concrete Details)
│   │       ├── api/                       # API HTTP delivery layer (FastAPI endpoints)
│   │       │   ├── v1/
│   │       │   │   ├── chat_router.py
│   │       │   │   ├── session_router.py
│   │       │   │   └── artifact_router.py
│   │       │   └── deps.py                # FastAPI dependency injection definitions
│   │       │   └── app.py                 # FastAPI application mount
│   │       ├── database/                  # SQL database migrations & schemas
│   │       │   ├── connection.py          # Session pools engine builders
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
│   ├── requirements.txt
│   └── alembic.ini
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

### 3.1 Domain Purity
* Files in `domain/` must remain pure Python files. They must not import FastAPI, SQLAlchemy, Alembic, or any model SDKs.
* Domain entities must be standard Python `dataclasses` or normal classes. They must not inherit from SQLAlchemy's `Base` or Pydantic's `BaseModel`.

### 3.2 Dependency Inversion (Ports & Adapters)
* High-level business logic must never instantiate concrete low-level implementation details.
* Use Cases and Skills must interact with databases, LLM engines, and vector indexes *strictly* through abstract Interface declarations (Ports).

### 3.3 Database & Vector Query Isolation
* Direct database queries or ORM models must never appear outside the `infrastructure/database/` directory.
* Direct vector calculations or vector-store specific queries (e.g. pgvector operator definitions) must never appear outside the `infrastructure/vectorstore/` directory.

### 3.4 Request & Response Serialization Boundary
* Pydantic schemas reside inside the `infrastructure/api/` layer or separate schema models. They represent serialization formats for network endpoints.
* Use cases receive parameters as primitive types or Domain Entities and return Domain Entities. 

### 3.5 Dependency Injection (DI) Rule
* Class dependencies must be declared in constructors (`__init__`) using type hints referencing abstract Interfaces (Ports).
* Concrete implementations are resolved and bound dynamically at request time using FastAPI's built-in dependency injection system via `Depends` in [`backend/app/infrastructure/api/deps.py`](file:///c:/Projects/lenny-growth-assistant/backend/app/infrastructure/api/deps.py). 
* Heavy enterprise container registries are forbidden.

---

## 5. Architectural Changes & Maintainability Improvements

### 1. Moving Skills to the Application Layer
* **Rationale:** AI Skills (RAG, Essay Writing, Artifact Generation) represent specific business goals and orchestration. They are not technical infrastructure elements like database tables or socket connections.
* **Benefit:** Grouping them alongside use cases ensures that business capabilities reside within application boundaries. This prevents domain interfaces from leaking details to infrastructure, keeps LLM orchestrations highly unit-testable without networking wrappers, and makes adding new capabilities as simple as adding a new Skill file under `application/skills/`.

### 2. Replacing Features with Use Cases
* **Rationale:** UI structures or page visual components change rapidly, while the backend's core operations are stable.
* **Benefit:** Reorienting backend operations around specific Use Cases (e.g., `send_message.py`) conforms to the Single Responsibility Principle. Each use case organizes exactly one operational flow, making the backend codebase easier to read, trace, and debug for both humans and AI models.

### 3. Adding a Vector Store Layer
* **Rationale:** Vector stores (pgvector, pinecone, chroma) are infrastructure details. Embedding calculations and vector-specific operators are technical details.
* **Benefit:** Consolidating embedding generation, retrieval queries, and vector database drivers in `infrastructure/vectorstore/` separates retrieval execution from use cases. The RAG skill inside `application/skills/` uses a pure interface port `IVectorStore`, allowing developer teams to migrate from pgvector to other services by editing only the infrastructure layer.

### 4. Improving Ingestion Separation
* **Rationale:** Ingestion scripts contain complex business rules for parsing, chunking, and preparing documents. When written directly in terminal scripts, this logic is difficult to test or integrate into server operations.
* **Benefit:** Moving parsing, chunking, embedding, and loading details into `infrastructure/ingestion/` makes the code reusable. The entrypoint scripts (`scripts/run_ingestion.py` and `scripts/seed_database.py`) remain clean, command-line wrappers with zero processing logic.

### 5. Leveraging Built-in FastAPI DI (Removal of container.py)
* **Rationale:** Introducing an external Dependency Injection framework adds unnecessary configuration boilerplate for an application of this scale.
* **Benefit:** Using FastAPI's native `Depends` system in `api/deps.py` accomplishes DI with zero extra packages, uses standard Python type hints, and integrates natively with routers.

### 6. Lean Skills (Removal of BaseSkill and Skill Registry)
* **Rationale:** Having only three skills means abstractions like `BaseSkill` and a dynamic `skills/registry.py` create unnecessary structural bloat.
* **Benefit:** The `router.py` can directly import and call `RAGSkill`, `Ship30Skill`, and `ArtifactSkill`. This simplifies debugging and navigation, keeping the codebase practical and easy to build in a 3-day assignment.