# Product Requirements Document (PRD)

**Project:** Lenny Growth Assistant
**Version:** 2.1
**Author:** Varun S
**Status:** Draft for 3-day build (due Aug 2, 2026 EOD)

**Changed in v2.1:** the agent layer was re-specified after evaluator clarification. The system is now built *on top of the Claude Agent SDK as its harness* rather than around a hand-written router with three peer LLM providers. Affects §6.3, §6.5, §7.1, §8, §9, §10, §11.1, §11.2, §11.7.

---

## 1. Problem Statement

Professionals consume long-form content like podcasts and newsletters to learn product management and growth. However:

- Information is spread across hundreds of episodes.
- Finding a specific insight is difficult.
- Synthesizing multiple episodes takes time.
- Turning that knowledge into publishable content requires manual effort.

**Goal:** build an AI-powered assistant that understands Lenny's Podcast transcripts and acts as an intelligent growth advisor — answering grounded questions, generating Ship30for30-style essays, and producing renderable artifacts, all inside one conversational workspace.

---

## 2. Goals

### Primary Goals
- **Conversational AI** — ask questions about product management, startups, and growth.
- **Grounded answers** — responses use only Lenny transcript knowledge; no hallucination, cited sources.
- **Ship30 skill** — convert transcript knowledge into a ~1250-word essay in the Ship30for30 style.
- **Artifact generation** — produce Markdown, HTML, or CSS on request.
- **Artifact viewer** — render generated artifacts side-by-side with chat.
- **LLM toggle** — switch between cloud (Anthropic) and local (Ollama) with one env var.
- **Agent harness** — skill selection is driven by the Claude Agent SDK's agent loop, extended with this project's own tools, persistence, and grounding rules.

### Non-Goals
- No authentication or multi-user accounts.
- No billing.
- No image generation.
- No collaborative editing.
- No production-scale deployment (this is a local-first evaluation build).
- **No second cloud provider.** OpenAI was cut in v2.1 — see §6.3.

---

## 3. Personas

| Persona | Use case |
|---|---|
| Product Manager | Learn PM concepts from transcripts |
| Startup Founder | Brainstorm growth ideas |
| Student | Study product management systematically |

---

## 4. User Stories

- **Chat:** As a user, I want to ask questions so I can learn from Lenny's podcast.
- **Essay:** As a user, I want a Ship30 essay so I can publish it online.
- **Artifact:** As a user, I want HTML generated so I can preview a UI idea.
- **Sessions:** As a user, I want multiple chats so conversations stay separate.

---

## 5. Scope & MVP Phasing

The real constraint on this project isn't features — it's **~3 days**. Cutting scope deliberately and documenting the cut is itself part of what's being evaluated (product sense, system design judgment).

| Day | Focus | Deliverable |
|---|---|---|
| **1** | Ingestion → chunking → pgvector → retrieval | A grounded answer to a real question, from the CLI or a bare API endpoint |
| **2** | Agent SDK harness → three tools → Ollama toggle → error handling | Harness dispatches to RAG / Ship30 / Artifact on both Claude and Ollama; named failures degrade gracefully |
| **3** | Frontend chat + artifact viewer + docs + video | End-to-end demo, README, design.md, ARCHITECTURE.md, agent transcripts folder |

**Sequencing note for Day 2:** wire the harness against **Ollama first**, not Anthropic. The cloud path is the low-risk one; the local path is both mandatory and the likeliest source of surprise (§9). Discovering an incompatibility on Day 2 morning is recoverable — on Day 3 evening it is not.

**Cuts to protect the timeline:**

| Cut | Replacement | Why |
|---|---|---|
| OpenAI provider | Anthropic only (cloud) | Brief requires *a* cloud provider; the Claude SDK is separately mandated. A third adapter bought nothing |
| Custom skill router | Claude Agent SDK owns the loop | Writing a harness was the original misreading of the brief; adopting one is both correct and less code |
| Rename chat | Skip | Not in the original brief; new/list/delete is sufficient |
| Monaco Editor for artifacts | `react-markdown` + `rehype-sanitize`; sandboxed `<iframe srcDoc>` | ~90% of the viewer experience for a fraction of the build time |
| ChromaDB as a second vector store | pgvector only | Avoids running two databases; Postgres is already required |
| Full streaming UX polish | Streaming works, but artifacts render once a message finishes | Avoids detecting a code fence mid-stream (§6.6) |

---

## 6. Functional Requirements

### 6.1 Session Management
- New Chat, Delete Chat, List/Load Chat History.
- Each session maintains its own message history and context window.
- Session state is **Postgres-backed, not harness-local** — the Agent SDK's own session handling is process-scoped and does not satisfy §7's restart-survival requirement.

### 6.2 Conversation Storage
Store per message: role, content, timestamp, and any linked artifact.

### 6.3 LLM Switching

Single env var remains the user-facing switch:

```
LLM_PROVIDER=anthropic   # or ollama
```

There is **no per-vendor provider class hierarchy**. `core/config.py` resolves the toggle into a base URL and model name for one client:

| `LLM_PROVIDER` | Base URL | Model | Auth |
|---|---|---|---|
| `anthropic` | Anthropic default | `claude-sonnet-*` | `ANTHROPIC_API_KEY`, required, checked at startup |
| `ollama` | `http://localhost:11434` | e.g. `qwen3-coder` | dummy key (client requires one, Ollama ignores it) |

This works because Ollama v0.14.0+ exposes an **Anthropic-compatible `/v1/messages` endpoint including tool use**, so the same harness and the same tool definitions run against both.

**Embeddings are independent of this toggle** and always run locally via `nomic-embed-text` on Ollama (see `design.md`). This is what makes the §7 offline guarantee real: with `LLM_PROVIDER=ollama`, both chat and retrieval resolve to localhost.

### 6.4 Knowledge Base (RAG)

```
GitHub repo (lennys-podcast-transcripts)
        │
     Parser → Chunker → Embeddings → pgvector → Retriever
                                                    │
                                          rag_query tool → harness → LLM
```

Answers must:
- Retrieve relevant chunks before generating.
- Cite the source episode (and ideally speaker/timestamp — see §11.3 Documents schema).
- Explicitly decline rather than guess when the transcripts don't cover the question. This is enforced at the tool boundary: the tool returns retrieved context plus citations and nothing else, and the system prompt forbids answering outside it.

### 6.5 Agent Harness & Skill Selection

**This section was rewritten in v2.1.** The v2.0 design specified a hand-written `router.py` that inspected tool-call output and dispatched to skills. That is an *agent harness*, written from scratch. The brief asks for the opposite: build on the Claude Agent SDK (or Pi) as the harness, and extend it.

**Harness vs. orchestration** — the distinction the rest of this section depends on:

- **Harness** = owns the agent loop: calls the model, receives `tool_use`, executes the tool, feeds back `tool_result`, repeats. **Supplied by the Claude Agent SDK.**
- **Orchestration** = what the tools do, plus session persistence, grounding rules, artifact typing, and error mapping. **Owned by this project.**

**Tools registered with the harness** (tool *choice* is the model's; tool *behaviour* is ours):

```json
[
  { "name": "rag_query",           "description": "Answer a product/growth question using only Lenny's transcripts" },
  { "name": "write_ship30_essay",  "description": "Write a ~1250-word Ship30for30-style essay from transcript knowledge" },
  { "name": "generate_artifact",   "description": "Generate a standalone Markdown or HTML/CSS artifact" }
]
```

The model's tool-choice *is* the routing. This is what "the agent decides which skill to use" (an explicit grading criterion) is really asking for — and now it is the SDK's loop making that call, not ours.

**What this project adds on top of the SDK** (the "improve the harness" requirement):

1. The three domain tools above, as in-process SDK tools.
2. A durable session bridge — harness turns persisted to Postgres and rehydrated on the next turn.
3. Grounding enforcement at the tool boundary (§6.4), not left to model discretion.
4. Structured artifact extraction from tool output → DB → viewer (§6.6).
5. Failure mapping into the chat-visible behaviours of §7.1.
6. Portability of the same tool set across cloud and local models.

**If the Agent SDK behaves unexpectedly against Ollama** (e.g. hits an unsupported sub-endpoint): test this first on Day 2 morning, not Day 3. The fix is almost certainly a config flag or disabling a specific SDK feature — not a second harness. Record whatever happens in `docs/agent-transcripts/`.

### 6.6 Artifact Viewer
- Detect artifact type (Markdown vs HTML/CSS) from the tool's structured output — not from parsing raw chat text.
- Markdown renders via `react-markdown` + `rehype-sanitize`.
- HTML/CSS renders inside a sandboxed `<iframe srcDoc="...">` (prevents generated code from touching the parent page/session).
- Viewer opens automatically alongside chat when an artifact is produced.

---

## 7. Non-Functional Requirements

| Requirement | Target |
|---|---|
| Response latency | <5s for RAG answers (cloud); local latency is best-effort and disclosed as such |
| Session persistence | Survives backend restart (Postgres-backed, not harness-local) |
| UI | Responsive, modern, works at desktop widths at minimum |
| Offline capability | Full pipeline runs with `LLM_PROVIDER=ollama` and no internet access after initial model pull |
| Local setup | Evaluator can run it with documented prerequisites, including any Node/Claude Code runtime the Agent SDK requires |

### 7.1 Error Handling (explicit — this is a named grading criterion)

| Failure | Behavior |
|---|---|
| Missing `ANTHROPIC_API_KEY` when `LLM_PROVIDER=anthropic` | Fail fast at startup naming the missing env var; never fail silently mid-conversation |
| Ollama unreachable or request times out | Chat-visible error ("Local model didn't respond — is Ollama running?") rather than a hung UI; configurable timeout, default 30s |
| Agent SDK incompatible with a specific Ollama sub-endpoint | Disable or configure the offending SDK feature; test Day 2 morning; never surface an SDK stack trace to the user |
| Database connection failure | API returns 503 with a clear body; frontend shows a banner rather than a blank chat; in-flight messages are not silently dropped |
| Tool raises / returns malformed output | Caught in the tool adapter, returned to the loop as a `tool_result` error so the model can recover, with an iteration cap to prevent runaway loops |
| Retrieval returns no relevant chunks | Tool returns empty context; model is instructed to say it couldn't find the answer, not to answer from general knowledge |

---

## 8. Testing Strategy

Minimal but real, given the timeline:

- **Skill bodies (unit):** the three skills are plain callables with no SDK dependency — test them directly against a fixture set of transcript chunks and a mock `IVectorStore`. This is the main payoff of keeping tool logic out of the harness.
- **Harness port (unit):** use cases are tested against a mock `IAgentHarness`; no network, no SDK.
- **API (integration):** session CRUD and one chat round-trip with a stubbed harness.
- **Frontend:** one or two smoke tests — send a message and confirm a response renders; trigger an artifact and confirm the viewer opens.
- **Manual end-to-end:** one full run each on Anthropic and Ollama before recording the video, exercising all three tools plus one deliberate error case (e.g. stop Ollama mid-conversation). This doubles as content for the required "what failed and how you fixed it" transcript.

---

## 9. Risks

| Risk | Mitigation |
|---|---|
| **Agent SDK compatibility with Ollama** | Ollama v0.14.0+ supports the Anthropic `/v1/messages` endpoint including tool use — the documented path. Test Day 2 morning; if a specific SDK feature causes a problem, disable or configure it. Record the outcome in `docs/agent-transcripts/` |
| **Agent SDK runtime prerequisites** (Node / Claude Code CLI alongside the Python package) | Verify against official docs and document explicitly in the README; an undocumented prerequisite makes a working build look broken on the evaluator's machine |
| Small local models choose tools poorly even when tool-calling works | Keep tool descriptions short and behaviourally distinct; pick a local model with solid tool support (e.g. a recent Qwen/Llama build); disclose local quality limits in the video |
| Large transcript corpus / embedding latency | Chunk and embed once at ingestion, not per-request |
| Hallucination | Grounding enforced at the tool boundary + explicit decline behaviour |
| Context overflow on long sessions | Cap retrieved chunks; cap harness loop iterations; truncate older turns when rehydrating history |
| Generated HTML/CSS could contain unsafe scripts | Rendered only in a sandboxed iframe, never injected into the parent DOM |

---

## 10. Success Criteria

- ✔ Multiple sessions, persisted across backend restarts
- ✔ The **Claude Agent SDK owns the agent loop**; no hand-written router remains in the application layer
- ✔ All three skills are registered as tools and selected by the model, not by our code
- ✔ Works with Ollama end-to-end, offline, via the Anthropic-compatible endpoint
- ✔ Works with Claude via the same harness and the same tools, toggled by one env var
- ✔ RAG answers are grounded and cite sources; out-of-corpus questions are declined
- ✔ Ship30 essay output matches the target structure and length
- ✔ Artifact viewer renders Markdown and HTML/CSS side-by-side with chat
- ✔ Named failure modes (§7.1) degrade gracefully, not silently

---

## 11. Technical Design

### 11.1 Architecture

```
                     React Frontend
                           │
                    FastAPI Backend
                           │
                   SendMessageUseCase
                  ┌────────┴────────┐
                  │                 │
         IAgentHarness         PostgreSQL
                  │            (+ pgvector)
         Claude Agent SDK
         (owns the loop)
                  │
            registered tools
         ┌────┼─────────────┐
         │    │             │
      rag_  write_ship30  generate_
      query   _essay       artifact
         │
   Retriever → pgvector → Embeddings (nomic-embed-text, local)
```

### 11.2 Tech Stack

**Frontend:** React, Vite, TypeScript, TailwindCSS v4, shadcn/ui, react-markdown + rehype-sanitize, sandboxed iframe
**Backend:** FastAPI, SQLAlchemy, Pydantic, Alembic
**Agent layer:** `claude-agent-sdk` (Python 3.10+) as the harness; `anthropic` client for the fallback loop
**Database:** PostgreSQL 16 + pgvector (single database, no second vector store)
**Models:** Anthropic Claude (cloud) or any Ollama model exposing the Anthropic-compatible endpoint (local)
**Embeddings:** `nomic-embed-text` via Ollama, always local, 768-dim

### 11.3 Database Schema

Unchanged from v2.0.

**ChatSession**
| Field | Type |
|---|---|
| id | UUID |
| title | text |
| created_at | timestamp |
| updated_at | timestamp |

**Messages**
| Field | Type |
|---|---|
| id | UUID |
| session_id | FK → ChatSession |
| role | enum(user, assistant) |
| content | text |
| artifact_id | FK → Artifacts, nullable |
| created_at | timestamp |

**Artifacts**
| Field | Type |
|---|---|
| id | UUID |
| session_id | FK → ChatSession |
| type | enum(markdown, html) |
| content | text |
| created_at | timestamp |

**Documents** (transcript chunks)
| Field | Type |
|---|---|
| id | UUID |
| title | text |
| source | text (GitHub path) |
| episode | text |
| speaker | text, nullable |
| timestamp_range | text, nullable — e.g. "12:04–13:10" |
| chunk | text |
| embedding | vector(768) |

Enum columns persist *values*, not member names (`user`/`assistant`, `markdown`/`html`) — see `design.md`.

### 11.4 API Design

All routes are mounted under a single `/api` prefix in `infrastructure/api/app.py`.

| Endpoint | Purpose |
|---|---|
| `POST /api/sessions` | Create session |
| `GET /api/sessions` | List sessions |
| `GET /api/sessions/{id}` | Get session + messages |
| `DELETE /api/sessions/{id}` | Delete session |
| `POST /api/chat` | Send message, get response (harness turn) |
| `POST /api/chat/stream` | Streaming variant |
| `GET /api/artifacts/{id}` | Fetch artifact |
| `POST /api/ingest` | Run ingestion pipeline |

`POST /artifacts` was removed: artifacts are created inside the harness turn by the `generate_artifact` tool and persisted by `SendMessageUseCase`. An external creation endpoint would be a second, unused write path.

### 11.5 Prompt Templates

**System prompt (harness-level)**
```
You are a growth advisor grounded in Lenny's Podcast transcripts.
You have three tools. Choose the one that fits the user's request.
Never answer product/growth questions from your own knowledge —
use rag_query and rely only on what it returns.
If a tool returns no relevant context, say so plainly.
```

**RAG (tool-level, wraps retrieved context)**
```
Answer ONLY using the retrieved context below.
If the answer isn't in the context, say:
"I couldn't find this in Lenny's transcripts."
Never invent information. Cite the episode (and speaker/timestamp if available).
```

**Ship30 (tool-level)**
```
Write a ~1250-word essay in the Ship30for30 style, using ONLY the
retrieved transcript context provided.

Structure:
- Strong hook (1-2 sentences, no throat-clearing)
- A concrete story or example from the transcripts
- 3-5 distilled lessons, each with a bolded one-line takeaway
- Heavy use of short paragraphs and bullet points for skimmability
- A single, clear closing takeaway

Do not introduce claims that aren't grounded in the retrieved context.
```

**Artifact (tool-level)**
```
Generate only valid Markdown or HTML/CSS based on the conversation context.
Return the artifact plus its type ("markdown" or "html") as structured
tool output. No explanation before or after.
```

### 11.6 Frontend

**Pages:** `/` (Chat + Artifact Panel + Session Sidebar), `/settings`
**Components:** Sidebar, ChatWindow, ChatBubble, MessageInput, ArtifactViewer, MarkdownRenderer, HTMLRenderer, SettingsModal, SessionList, TopBar

### 11.7 Folder Structure

The v2.0 flat layout in this section was stale and conflicted with `ARCHITECTURE.md`. **The canonical tree now lives in `ARCHITECTURE.md` §3 only.** Summary of the backend shape:

```
backend/app/
  core/            # config (incl. LLM toggle resolution), logging
  domain/          # entities + ports (IRepository, IAgentHarness, IVectorStore)
  application/     # use_cases/ + skills/  ← tool LOGIC, no SDK import, no agent loop
  infrastructure/
    api/           # FastAPI routers, schemas, deps
    database/      # SQLAlchemy models + repositories
    harness/       # tool REGISTRATION + the agent loop (Agent SDK / fallback)
    vectorstore/   # embeddings, retriever, pgvector driver
    ingestion/     # parser, chunker, embedder, loader
```

---

## 12. Future Work

- Authentication
- Export conversations
- Restore an OpenAI adapter if multi-cloud is ever needed
- Image generation
- Collaborative editing
- Mobile app