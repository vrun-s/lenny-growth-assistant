# Product Requirements Document (PRD)

**Project:** Lenny Growth Assistant
**Version:** 2.0
**Author:** Varun S
**Status:** Draft for 3-day build (due Aug 2, 2026 EOD)

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
- **LLM toggle** — switch between cloud (Anthropic/OpenAI) and local (Ollama) with one env var.

### Non-Goals
- No authentication or multi-user accounts.
- No billing.
- No image generation.
- No collaborative editing.
- No production-scale deployment (this is a local-first evaluation build).

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

This is new in v2.0 and exists because the real constraint on this project isn't features — it's **~3 days**. Cutting scope deliberately and documenting the cut is itself part of what's being evaluated (product sense, system design judgment). The plan below assumes solo, sequential work; compress further if needed.

| Day | Focus | Deliverable |
|---|---|---|
| **1** | Ingestion → chunking → pgvector → basic RAG | Can answer a question grounded in transcripts, from the CLI or a bare API endpoint |
| **2** | Skill routing (tool-use) → Ship30 skill → Ollama toggle → error handling | Agent correctly dispatches to RAG / Ship30 / Artifact skill on both Claude and Ollama |
| **3** | Frontend chat + artifact viewer + docs + video | End-to-end demo, README, design.md, ARCHITECTURE.md, agent transcripts folder |

**Cuts from v1.0 to protect the timeline:**

| Cut | Replacement | Why |
|---|---|---|
| Rename chat | Skip | Not in the original brief; new/list/delete is sufficient |
| Monaco Editor for artifacts | `react-markdown` + `rehype-sanitize` for Markdown; sandboxed `<iframe srcDoc>` for HTML/CSS | Gets ~90% of the "artifact viewer" experience for a fraction of the build time |
| ChromaDB as a second vector store option | pgvector only | Avoids running two databases; Postgres is already required |
| Full streaming UX polish | Streaming works, but artifacts render only once a message finishes | Avoids the added complexity of detecting a code fence mid-stream (see §6.6) |

If time allows after Day 3, restore items from this list in the order listed — pgvector-first was a fixed decision, not a stretch item.

---

## 6. Functional Requirements

### 6.1 Session Management
- New Chat, Delete Chat, List/Load Chat History.
- Each session maintains its own message history and context window.

### 6.2 Conversation Storage
Store per message: role, content, timestamp, and any linked artifact.

### 6.3 LLM Switching
Single env var controls provider:

```
LLM_PROVIDER=anthropic   # or openai / ollama
```

All providers implement a common `BaseProvider` interface (see §11.3) so the rest of the app is provider-agnostic.

### 6.4 Knowledge Base (RAG)

```
GitHub repo (lennys-podcast-transcripts)
        │
     Parser
        │
     Chunker
        │
    Embeddings
        │
   Vector DB (pgvector)
        │
    Retriever
        │
       LLM
```

Answers must:
- Retrieve relevant chunks before generating.
- Cite the source episode (and ideally timestamp — see §11.3 Documents schema).
- Explicitly decline rather than guess when the transcripts don't cover the question.

### 6.5 Skill Routing — Agentic Architecture

This is the section most under-specified in v1.0, and it's the first thing the evaluators said they'd look at, so it gets its own detail here rather than a one-line diagram.

**Primary path (cloud providers — Anthropic/OpenAI):** use native tool-calling. Define three tools and let the model choose:

```json
[
  { "name": "rag_query", "description": "Answer a product/growth question using only Lenny's transcripts" },
  { "name": "write_ship30_essay", "description": "Write a ~1250-word Ship30for30-style essay from transcript knowledge" },
  { "name": "generate_artifact", "description": "Generate a standalone Markdown or HTML/CSS artifact" }
]
```

The model's tool-choice *is* the router. This is more robust than a keyword classifier and is what "agent decides which skill to use" (an explicit grading criterion) is really asking for.

**Fallback path (local — Ollama):** small local models are inconsistent at reliable function-calling. Rather than assume tool-use works locally, the router degrades gracefully:

1. Try native tool-calling if the loaded Ollama model supports it (e.g., recent Llama/Qwen builds).
2. If unsupported or the model returns malformed tool-call output, fall back to a lightweight prompted classifier: a single short LLM call that returns one of `RAG | SHIP30 | ARTIFACT | GENERAL`, parsed defensively (default to `RAG` on any parse failure).

This fallback is a first-class part of the design, not an afterthought — it's what makes "mandatory local demo" actually work end-to-end. It's called out again in Risks (§9).

### 6.6 Artifact Viewer
- Detect artifact type (Markdown vs HTML/CSS) from the tool call's structured output — not from parsing the raw chat text.
- Markdown renders via `react-markdown`.
- HTML/CSS renders inside a sandboxed `<iframe srcDoc="...">` (prevents generated code from touching the parent page/session).
- Viewer opens automatically alongside chat when an artifact is produced.

---

## 7. Non-Functional Requirements

| Requirement | Target |
|---|---|
| Response latency | <5s for RAG answers (cloud); local latency is best-effort and disclosed as such |
| Session persistence | Survives backend restart (Postgres-backed) |
| UI | Responsive, modern, works at desktop widths at minimum |
| Offline capability | Full pipeline must run with `LLM_PROVIDER=ollama` and no internet access after initial model pull |

### 7.1 Error Handling (explicit — this is a named grading criterion)

| Failure | Behavior |
|---|---|
| Missing API key (Anthropic/OpenAI) | Fail fast at startup with a clear message naming the missing env var; don't fail silently mid-conversation |
| Ollama unreachable or request times out | Return a chat-visible error message ("Local model didn't respond — is Ollama running?") rather than hanging the UI; configurable timeout, default 30s |
| Database connection failure | API returns 503 with a clear error body; frontend shows a banner rather than a blank chat; in-flight messages are not silently dropped |
| Malformed tool-call output (local models) | Caught and routed through the fallback classifier (§6.5), not surfaced as a raw error |
| Retrieval returns no relevant chunks | Model is instructed to say it couldn't find the answer in the transcripts, rather than answering from general knowledge |

---

## 8. Testing Strategy

Minimal but real, given the timeline:

- **Backend:** pytest covering the provider interface (mock each provider), the router's fallback logic, and the RAG retrieval function against a small fixture set of transcript chunks.
- **Frontend:** one or two smoke tests (e.g., Playwright) — send a message, confirm a response renders; trigger an artifact, confirm the viewer opens.
- **Manual end-to-end pass:** one full run each on Anthropic and Ollama before recording the demo video, specifically exercising all three skills plus one deliberate error case (e.g., stop Ollama mid-conversation) — this doubles as content for the required "what failed and how you fixed it" transcript.

---

## 9. Risks

| Risk | Mitigation |
|---|---|
| Large transcript corpus / embedding latency | Chunk and embed once at ingestion, not per-request; cache embeddings |
| Hallucination | Strict "answer only from context" prompt + explicit decline behavior |
| Context overflow on long sessions | Cap retrieved chunks; summarize older turns if needed |
| **Local models unreliable at tool-calling** | Fallback prompted classifier (§6.5) — this is the biggest risk to the *mandatory* local demo and is treated as a core design requirement, not a stretch goal |
| Generated HTML/CSS could contain unsafe scripts | Rendered only in a sandboxed iframe, never injected into the parent DOM |

---

## 10. Success Criteria

- ✔ Multiple sessions, persisted across restarts
- ✔ Works with Ollama (with graceful fallback routing)
- ✔ Works with Claude and/or OpenAI
- ✔ RAG answers are grounded and cite sources
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
          ┌───────────┴───────────┐
          │                       │
     Agent Router             PostgreSQL
          │                   (+ pgvector)
   ┌──────┼────────┐
   │      │        │
 RAG   Ship30   Artifact
 Skill  Skill    Skill
   │
Retriever → pgvector → Embeddings → Lenny Transcripts
```

### 11.2 Tech Stack

**Frontend:** React, Vite, TypeScript, TailwindCSS, shadcn/ui, react-markdown, sandboxed iframe (HTML/CSS artifacts)
**Backend:** FastAPI, SQLAlchemy, Pydantic, Alembic
**Database:** PostgreSQL + pgvector (single database, no second vector store)
**LLM layer:** `BaseProvider` → `AnthropicProvider`, `OpenAIProvider`, `OllamaProvider`

### 11.3 Database Schema

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
| speaker | text, nullable — *added in v2.0 for finer-grained citation* |
| timestamp_range | text, nullable — *added in v2.0, e.g. "12:04–13:10", enables citing the moment, not just the episode* |
| chunk | text |
| embedding | vector |

### 11.4 API Design

| Endpoint | Purpose |
|---|---|
| `POST /sessions` | Create session |
| `GET /sessions` | List sessions |
| `GET /sessions/{id}` | Get session + messages |
| `DELETE /sessions/{id}` | Delete session |
| `POST /chat` | Send message, get response |
| `POST /chat/stream` | Streaming variant |
| `GET /artifacts/{id}` | Fetch artifact |
| `POST /artifacts` | Create artifact (internal, used by Artifact Skill) |
| `POST /ingest` | Run ingestion pipeline |
| `POST /reindex` | Rebuild embeddings |

### 11.5 Prompt Templates

**RAG**
```
Answer ONLY using the retrieved context below.
If the answer isn't in the context, say:
"I couldn't find this in Lenny's transcripts."
Never invent information. Cite the episode (and speaker/timestamp if available).
```

**Ship30**
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

**Artifact**
```
Generate only valid Markdown or HTML/CSS based on the conversation context.
Return the artifact inside a single fenced code block.
No explanations before or after the code block.
```

### 11.6 Frontend

**Pages:** `/` (Chat + Artifact Panel + Session Sidebar), `/settings`
**Components:** Sidebar, ChatWindow, ChatBubble, MessageInput, ArtifactViewer, MarkdownRenderer, HTMLRenderer, SettingsModal, SessionList, TopBar

### 11.7 Folder Structure

```
lenny-growth-assistant/
  frontend/
    components/
    pages/
    hooks/
    services/
    types/
  backend/
    api/
    agents/
    providers/
    rag/
    prompts/
    models/
    schemas/
    services/
    repositories/
    core/
      config.py
      database.py
      vectorstore.py
    ingestion/
    scripts/
  docs/
    PRD.md
    ARCHITECTURE.md
    design.md
    README.md
    agent-transcripts/        ← added in v2.0, required by the brief
```

---

## 12. Future Work

- Authentication
- Export conversations
- Image generation
- Collaborative editing
- Mobile app