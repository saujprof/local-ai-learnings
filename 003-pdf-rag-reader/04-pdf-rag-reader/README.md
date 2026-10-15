# 04 - Scalable PDF RAG

Implementation record: [Unit 12 integration plan](INTEGRATION_PLAN.md).

V4 turns the earlier RAG experiments into a small end-to-end application that someone can clone, run, upload PDFs to, and ask questions against.

The goal is to move from a learning script to a **production-shaped RAG system** with clear application boundaries.

**Project status: complete.** All planned V4 units, live integration checks, and
the small-model chat/RAG router are implemented. Document-scope optimization
and GPU latency tuning are optional follow-up experiments.

## Quick start

Run from `003-pdf-rag-reader/04-pdf-rag-reader`. Requirements: Docker with
Compose, host Ollama, and Node 22.18+ for frontend tooling/tests. Python 3.11+
is needed only for running the backend/tests directly; the container uses 3.12.

1. Start Docker (enable this distro's WSL integration when applicable).
2. Start host Ollama and install the configured models:

   ```sh
   ollama pull qwen3:8b
   ollama pull qwen3-embedding:8b
   ollama pull qwen2.5:0.5b
   ```

3. Copy `.env.example` to `.env` if no `.env` exists. Adjust `OLLAMA_URL` for
   your host. Ollama must listen on an interface reachable from Docker.
4. Start and check services:

   ```sh
   docker compose up --build -d
   docker compose exec backend python -m scripts.check_connections
   ```

5. In another terminal, start the UI:

   ```sh
   cd ui
   npm ci
   npm run dev
   ```

Open the URL printed by Vite (normally `http://localhost:5173`). Upload a small
text PDF, wait for Ready, then ask a question. API documentation is available at
`http://127.0.0.1:8000/api-docs`.

## Configuration and troubleshooting

| File | Purpose |
| --- | --- |
| Root `.env` | Compose variables: backend port, host Ollama URL/models, collection and retrieval settings |
| `be/.env` | Direct Python backend runs only; not loaded by Compose |
| `ui/.env.local` | Optional Vite settings; copy from `ui/.env.example` |

Default ports: UI 5173, backend 8000. Qdrant is internal to Compose on 6333.
The UI proxies `/api` to `http://127.0.0.1:8000`; if `BACKEND_PORT` changes, set
`API_PROXY_TARGET` in `ui/.env.local` and restart Vite. Production hosting needs
its own `/api` reverse proxy, or an absolute API URL plus backend CORS setup.

- **API unavailable:** check `docker compose ps`, backend logs, and UI proxy URL.
- **Model unavailable:** run the connection check; confirm model names and host
  Ollama binding. `localhost` inside a container is not the host machine.
- **Failed PDF:** inspect the document error. Scanned PDFs need OCR, which is not
  included. Delete failed documents before reuploading to clean partial vectors.
- **Interrupted processing/deletion:** restart marks the record Failed. Delete
  and reupload; incomplete vectors are excluded because retrieval uses Ready IDs.
- **Uncertain chat timeout:** refresh history before retrying; the request may
  have saved a response or still be processing. There are no automatic retries.
- **Changing embedding models:** use a new collection and reindex all PDFs;
  matching vector dimensions do not make different models compatible.

Named volumes retain PDFs, registry/history, and Qdrant data. `docker compose down`
retains volumes; `docker compose down --volumes` deletes them.

## Verification and limits

All planned units are implemented. See [integration record](INTEGRATION_PLAN.md),
[runtime checks](RUNTIME_VERIFICATION.md), and
[browser/backend acceptance](END_TO_END_VERIFICATION.md).

```sh
# From be, after creating/activating its virtual environment:
python -m pip install -r requirements-dev.txt
python -m pytest -q

# From ui:
npm run test:http
npm run build
```

V4 is a single-user learning application: use one backend worker. JSON storage
locks coordinate one process, not multiple workers. Ingestion is serialized;
there is no durable job queue, OCR, authentication, streaming, or multi-user
history isolation. History offsets assume one active UI session. Recent model
context is bounded; conversation summarization is not implemented. A successful
fixture test does not establish answer quality for arbitrary PDFs. Dependency
ranges and container tags are not fully locked for reproducible builds.

Retrieval currently searches vectors from every Ready PDF and relies on semantic
ranking to select evidence, even when a question names one document. On
constrained GPUs, model loading plus embedding, reranking, and answer generation
can exceed the configured dependency timeout. Both are accepted V4 limitations.

## Stack

```text
UI         → Vue 3
Backend    → FastAPI
Vector DB  → Qdrant
LLM        → Ollama / qwen3:8b
Embeddings → Ollama / qwen3-embedding:8b
Router     → Ollama / qwen2.5:0.5b
```

## High-Level Architecture

```text
Vue 3 UI
   ↓ HTTP
FastAPI
   ├── Local PDF storage
   ├── Document registry
   ├── Chat history
   ├── Qdrant
   └── Ollama
```

## Main User Flow

```text
User opens web app
↓
Uploads one or more PDFs
↓
Backend processes and indexes them
↓
User asks a question
↓
System retrieves relevant chunks from indexed PDFs
↓
LLM answers from retrieved context
↓
UI shows answer + PDF/page citations
```

## Features

- upload PDFs
- list uploaded PDFs
- show document processing status
- delete PDFs
- process PDFs into page-aware chunks
- generate embeddings
- store vectors and metadata in Qdrant
- search across indexed PDFs
- Top-K retrieval
- relative similarity filtering
- LLM reranking
- grounded answer generation
- PDF/page citations
- small-model routing for casual chat versus document RAG
- basic chat history
- compact older conversation context when needed

## Document Lifecycle

Each uploaded PDF gets a unique document ID and status.

```text
processing
ready
failed
deleting
```

Example registry entry:

```json
{
  "id": "doc_123",
  "name": "report.pdf",
  "path": "./uploads/doc_123.pdf",
  "status": "processing",
  "created_at": "..."
}
```

For this version, a JSON registry is enough. The focus is the RAG architecture rather than relational application storage.

## Upload / Ingestion Flow

```text
POST /docs
↓
save PDF
↓
create document ID
↓
mark document as processing
↓
return upload response
↓
extract text
↓
create page-aware chunks
↓
generate embeddings
↓
store vectors + metadata in Qdrant
↓
mark document as ready
```

Example Qdrant point:

```json
{
  "id": "chunk_uuid",
  "vector": [],
  "payload": {
    "document_id": "doc_123",
    "document_name": "report.pdf",
    "chunk_id": 8,
    "page_start": 3,
    "page_end": 4,
    "text": "..."
  }
}
```

## Delete Flow

```text
DELETE /docs/{id}
↓
mark document as deleting
↓
delete all Qdrant points for document_id
↓
delete local PDF
↓
remove document from registry
```

## Query Flow

```text
POST /chat
↓
load bounded recent history
↓
qwen2.5:0.5b classifies GENERAL or RAG using at most one previous turn
↓
GENERAL: a separate history-free small-model call answers and saves the turn

RAG:
question embedding
↓
Qdrant Top-K search
↓
relative similarity filtering
↓
LLM reranking
↓
final chunks
↓
build grounded context
↓
LLM answer
↓
attach citations
↓
save chat history
↓
return answer
```

Router failures and invalid structured output fall back to RAG. This keeps
document questions on the grounded path. GENERAL messages can be answered when
no document is Ready; RAG messages still require at least one Ready document.

For V4, chat requests can remain synchronous.

PDF ingestion is a better candidate for background processing because large PDFs may require many chunk and embedding operations.

## Citations

Citations should come from backend-owned metadata rather than only from text generated by the LLM.

Example response:

```json
{
  "answer": "...",
  "sources": [
    {
      "document_id": "doc_123",
      "document_name": "report.pdf",
      "page_start": 4,
      "page_end": 4,
      "chunk_id": 18
    }
  ]
}
```

## Chat History

Keep two separate concepts:

```text
Full chat history
→ used for UI/storage

LLM conversation context
→ limited by the model context window
```

Initially, send only the most recent N messages to the model.

Later:

```text
conversation summary
+
recent messages
+
retrieved document context
+
current question
```

Conversation memory helps understand the discussion, but PDF evidence still comes from retrieved chunks.

## API Sketch

```text
GET    /docs
POST   /docs
DELETE /docs/{id}

GET    /chat?limit=10&offset=0
POST   /chat
```

## Suggested Backend Structure

```text
backend/
├── app/
│   ├── main.py
│   ├── api/
│   │   ├── documents.py
│   │   └── chat.py
│   ├── services/
│   │   ├── pdf_service.py
│   │   ├── embedding_service.py
│   │   ├── retrieval_service.py
│   │   ├── reranker_service.py
│   │   └── llm_service.py
│   ├── vector_store/
│   │   └── qdrant_store.py
│   ├── models/
│   └── config.py
├── uploads/
└── tests/
```

## Qdrant's Role

Qdrant replaces the local FAISS + JSON vector-search setup from V3.

FAISS gave us:

```text
store vectors
search vectors
Top-K results
persist/load index
```

Qdrant adds database behavior around that:

- persistent vector storage
- stable point IDs
- vector + metadata storage
- metadata filtering
- delete by document ID
- easier multi-document lifecycle
- API-based access
- concurrent access

A later production system may use:

```text
Postgres
→ users, documents, permissions, chat history, jobs

Qdrant
→ chunk vectors and retrieval metadata
```

That is intentionally outside the first V4 scope.

## What Makes This Production-Shaped

This version introduces the same major boundaries used by real RAG systems:

```text
frontend
backend API
document ingestion
embedding service
vector database
retrieval
reranking
generation
citations
document lifecycle
chat history
```

It is not yet fully production-hardened.

Authentication, multi-tenancy, job queues, retries, monitoring, hybrid search, advanced parsing, and evaluation can come later.

## Learning Goal

V3 answered:

> How does vector search work?

V4 answers:

> How do we build an application around vector search?

Progression:

```text
manual cosine search
↓
FAISS
↓
Qdrant
↓
multi-document RAG application
```

## Running with Docker Compose (Backend Unit 3)

Prerequisites: Docker Engine/Desktop with Compose v2, and Ollama running on the
host with the configured models installed. In WSL, enable Docker Desktop's WSL
integration for this distro and confirm `docker compose version` works.

From this project directory:

```sh
cp .env.example .env
docker compose config
docker compose up --build -d
docker compose ps
curl http://127.0.0.1:8000/health
docker compose exec backend python -m scripts.check_connections
```

The last command checks backend, Qdrant, and Ollama reachability from inside the
backend container, plus the presence of both configured models. It exits nonzero
on failure. Retry after Qdrant/Ollama have started; Compose's dependency ordering
only waits for the Qdrant container to start, not for readiness. Backend health
checks liveness only, so a healthy backend does not imply dependencies are ready.

API docs: `http://127.0.0.1:8000/api-docs`. The UI runs separately and calls the real backend through its Vite proxy.
Collections are created during indexing.

Compose reads the root `.env`; it does not load `be/.env`. Backend URLs differ
inside containers: Qdrant is `http://qdrant:6333`, and host Ollama defaults to
`http://host.docker.internal:11434`. Override `OLLAMA_URL` for your host setup.
If Ollama listens only on host loopback, configure it to listen on an interface
reachable from Docker, with access limited to your local environment.

The backend runs as a non-root user, with one worker and no development reload.
Only the backend port is published, on host loopback. Qdrant stays on the Compose
network. Named volumes preserve PDFs, registry/history, and Qdrant storage.

### Reviewing persistence

For an optional filesystem-only persistence check, use temporary marker files:

```sh
docker compose exec backend python -c "from pathlib import Path; Path('/app/uploads/unit3-check').write_text('ok'); Path('/app/data/unit3-check').write_text('ok')"
docker compose down
docker compose up -d
docker compose exec backend python -c "from pathlib import Path; assert Path('/app/uploads/unit3-check').read_text() == 'ok'; assert Path('/app/data/unit3-check').read_text() == 'ok'; print('Storage survived recreation')"
```

Live vector persistence was verified with an indexed fixture in unit 12.4. Qdrant's
`/qdrant/storage` already uses a named volume. `docker compose down` retains
volumes; adding `--volumes` deletes their data.

Use `docker compose logs backend qdrant` for troubleshooting. Rebuild after
backend code/dependency changes with `docker compose up --build -d`.

Image build, live connectivity, and volume persistence checks passed. See
[RUNTIME_VERIFICATION.md](RUNTIME_VERIFICATION.md) for evidence.

References: [Compose networking](https://docs.docker.com/compose/how-tos/networking/)
and [Qdrant installation](https://qdrant.tech/documentation/install/).
