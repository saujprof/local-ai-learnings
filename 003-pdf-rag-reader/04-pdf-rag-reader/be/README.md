# V4 Backend - PDF RAG API

The V4 backend is a FastAPI service that handles PDF upload, document processing, vector storage, retrieval, chat, and citations.

```text
HTTP server      -> FastAPI
PDF processing   -> asynchronous/background
Vector database  -> Qdrant container
Chat requests    -> synchronous
LLM/Embeddings   -> Ollama running on host
Runtime          -> Docker Compose for backend + Qdrant
```

## Implementation Units

Implement and review one unit at a time. Units 1 and 2 are implemented; unit 3 is implemented with live Docker verification pending; units 4–6 are implemented; units 7–12 are pending.

The request/response shapes, status codes, pagination, and error format are
defined in [API_CONTRACT.md](API_CONTRACT.md). Health and local document routes are implemented; chat routes remain pending.
UI units 1–4 already use mocks; real UI integration remains deferred until the
backend APIs are ready.

| Unit | Scope | Review check |
| --- | --- | --- |
| 1. API contract | Define document, message, citation, pagination, and error schemas; agree on request bodies and response codes. | Example payloads match the existing UI types and document/chat flows. |
| 2. FastAPI foundation | Create the app, environment configuration, dependency setup, and a health endpoint. | App starts locally; health endpoint responds; invalid configuration produces a useful error. |
| 3. Container setup | Add backend Dockerfile and root Compose configuration for backend + Qdrant, persistent volumes, and host Ollama connectivity. | Health endpoint is reachable; backend can reach Qdrant and host Ollama; stored data survives container recreation. |
| 4. Local persistence | Implement document registry and chat-history repositories with coordinated, atomic JSON writes. | Round-trip, restart, and concurrent-update checks preserve records without lost writes. |
| 5. Document APIs | Implement PDF validation, upload storage, document listing, and deletion of local files/registry entries. | Upload returns a Processing document; list survives restart; invalid uploads are rejected; failed deletion retains the registry entry. Ingestion is not wired yet. |
| 6. PDF extraction and chunking | Extract page-aware text and produce chunks carrying document/page metadata. | A small multi-page fixture produces traceable chunks; empty or unreadable PDFs report useful failures. |
| 7. Embeddings and vector storage | Add Ollama embedding client and Qdrant collection, upsert, search, and delete operations. | Fixture chunks can be embedded, stored, retrieved, and deleted by document ID; vector dimensions are checked. |
| 8. Ingestion lifecycle | Connect background ingestion to upload, update Ready/Failed states, clean up vectors on deletion, coordinate deletion with ingestion, and handle interrupted jobs on restart. | A PDF reaches Ready or Failed; deleting during ingestion leaves no orphan vectors; restart does not leave documents stuck indefinitely. |
| 9. Retrieval and reranking | Add question embedding, Top-K retrieval, relative filtering, and LLM reranking. | A known question selects relevant fixture chunks; empty results and malformed reranking output have defined behavior. |
| 10. Answer generation | Build grounded prompts and return answers with metadata-based citations; define the no-evidence response. | Fixture questions produce answers with valid document/page references; no-evidence queries avoid unsupported answers. |
| 11. Chat APIs and history | Wire synchronous POST /chat, persist completed turns, expose paginated GET /chat, and include bounded recent conversation context. | A chat turn returns answer + sources; reload and multiple history pages preserve ordering and IDs; failed requests do not save partial turns. |
| 12. UI integration | Replace mocks with Axios calls, configure API access, poll document status, and expose API errors with recovery actions. | Upload → Ready → ask → citations → reload history → delete works through the real UI and backend. |

### Contract Decisions for Unit 1

- Use stable IDs for stored chat messages. History pages return
  `{ "messages": [...], "hasMore": true }`; offsets count individual messages
  from newest, while each returned page is ordered oldest to newest.
- Specify the multipart upload field, document-list envelope, successful delete
  response, and API error format before implementing the routes.
- Reserve `/docs` for document APIs and choose a separate path for interactive
  API documentation.
- Define whether deletion completes within its HTTP request. The current UI
  removes a document only after the service confirms completion.

### Boundaries

- Units 5–7 provide pieces independently; unit 8 connects actual ingestion.
  Until then, an uploaded document staying Processing is expected.
- Persist both `uploads/` and `data/`, plus Qdrant storage.
- Start with one backend process and coordinate JSON writes and document jobs
  within that process. Multiple workers require a different coordination plan.
- Use bounded recent messages for initial LLM context. Conversation summarization
  can be a separate follow-up after the end-to-end flow works.
- Add focused checks with each behavior change, and document how to review each
  completed unit. Do not mark live integration checks passed using mocks alone.

## Running the Backend Locally (Unit 2)

Requires Python 3.11 or newer. From the `be` directory:

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
cp .env.example .env
uvicorn app.main:create_app --factory --reload --host 127.0.0.1 --port 8000
```

- `GET http://127.0.0.1:8000/health` returns `{"status":"ok"}`.
- Interactive API docs: `http://127.0.0.1:8000/api-docs`.
- OpenAPI schema: `http://127.0.0.1:8000/openapi.json`.
- `/docs` supports upload, list, and local deletion; `/chat` is not implemented yet.

Health is a liveness check, not proof that Qdrant or Ollama is reachable.
No external service is required to start this unit. Docker comes in unit 3.

Settings load from `.env` in the working directory; environment variables take
precedence. See `.env.example` for local defaults. URL schemes, model names, and
positive upload limits are validated at startup. Relative storage paths resolve
from the working directory. Storage directories are not created until the
persistence units. For containers, configure service/host-gateway URLs in unit 3.

Run focused checks:

```sh
python -m pytest -q
```

Checks cover health/docs routes, configuration validation and precedence, and
consistent validation/HTTP/application/unexpected-error envelopes. API errors do
not expose unexpected exception details to clients. The current dependency files
specify compatible version ranges; a reproducible dependency lock can be added
with the container setup.

## Local Persistence (Unit 4)

`app/storage/repositories.py` provides document and chat repositories, available
as `app.state.documents` and `app.state.chat_history`. They use the configured
`DATA_DIR` for `documents.json` and `chat_history.json`. Directories/files are
created on the first write, and existing records are loaded on each operation.

Document operations support add, get, newest-first list, status update, and
registry removal. Removing a registry record does not delete PDFs or vectors;
that coordination belongs to the later lifecycle service. These are internal
records containing storage paths; future routes must project public fields.

Chat writes append a whole completed question/answer pair atomically, assigning
stable IDs and UTC timestamps. Pages follow the API contract's message offsets
and chronological page order. Citations remain stored with the answer.

A shared lock per resolved file path protects read-modify-write operations
across threads and repository instances in one process. Writes flush and fsync a
temporary file in the same directory, then atomically replace the destination.
Failed replacement preserves the previous file and cleans up the temporary file.
Invalid stored data raises `StorageError` and is never silently reset.

Run one backend worker. Locks do not coordinate separate processes, containers,
or external file editors. Atomic replacement prevents partial JSON files, but
this is not a transactional database or a guarantee against all power-loss
scenarios. Async routes should call these blocking repositories in a thread pool.

Review checks:

```sh
python -m pytest tests/test_storage.py -q
```

Tests cover repository recreation, lifecycle updates, concurrent instances,
history pagination, failed replacement, and corrupt-file preservation. Document endpoints are implemented in unit 5; chat HTTP endpoints remain pending.

## Document APIs (Unit 5)

`app/api/documents.py` implements upload, list, and local deletion. Reinstall
`requirements-dev.txt` for the multipart parser and `pypdf`, or rebuild Docker.

With the server running:

```sh
curl -F 'file=@/path/to/report.pdf' http://127.0.0.1:8000/docs
curl http://127.0.0.1:8000/docs
curl -i -X DELETE http://127.0.0.1:8000/docs/DOCUMENT_ID
```

Upload returns 202 and a Processing document after saving it and the registry.
Names are display-only; files use generated IDs. Responses omit internal paths.
Duplicate filenames are allowed. PDFs must be nonempty, parseable, unencrypted,
and have at least one page. The configured byte limit applies to the uploaded
file; multipart parsing occurs first, so this is not a network-level request-body
limit. A deployment proxy can enforce a total request limit later.

Deletion returns 204 after removing the PDF and registry entry. Missing files
are tolerated on retry. A failed deletion keeps a Failed record with an error.
Registry operations coordinate local concurrent requests within one process.

Ingestion and vector deletion are not wired until unit 8. Documents therefore
remain Processing in this unit. UI integration is still deferred.

Tests cover upload validation/cleanup, unique IDs, hidden internal paths, restart
persistence, deletion, and failure/retry. Run `python -m pytest -q`.

## PDF Extraction and Chunking (Unit 6)

`app/services/pdf_service.py` provides `extract_pages`, `chunk_pages`, and
`process_pdf`. It uses the existing `pypdf` dependency and requires no external
services. `process_pdf` returns typed chunks containing `document_id`,
`document_name`, sequential zero-based `chunk_id`, `page_start`, `page_end`, and
`text`. Use `dataclasses.asdict` when preparing vector payloads in unit 7.

The initial strategy uses 1,000-character windows with 150-character overlap,
configurable through function arguments. Whitespace is normalized before
chunking. Chunks stay within a single page, so start/end page numbers are equal.
Blank pages produce no chunks but retain their place in the one-based PDF page
numbering. Unlike V3's cross-page packing, this favors simple, exact citations;
windows can split words, and paragraph/table layout is not preserved.

Unreadable, encrypted, or entirely text-free PDFs raise `PDFProcessingError`
with useful messages. OCR is not included. The service only extracts/chunks;
background jobs, embeddings, and status updates remain for later units.

```python
from pathlib import Path
from app.services.pdf_service import process_pdf

chunks = process_pdf(Path('uploads/example.pdf'), 'doc_123', 'example.pdf')
```

Run `python -m pytest tests/test_pdf_service.py -q` to review extraction from a
real generated multi-page PDF, blank-page numbering, chunk overlap/coverage,
invalid configuration, encryption, and unreadable/text-free inputs.

## Responsibilities

The backend is responsible for:

- exposing HTTP APIs for documents and chat
- storing uploaded PDFs
- tracking document processing status
- processing PDFs in the background
- extracting text and creating page-aware chunks
- generating embeddings
- storing vectors and metadata in Qdrant
- deleting vectors when a PDF is deleted
- handling synchronous chat requests
- retrieving and reranking relevant chunks
- generating grounded answers
- returning PDF/page citations
- storing basic chat history

## High-Level Architecture

```text
Vue 3 UI
   |
   v
FastAPI HTTP Server
   |
   +-- Mounted PDF storage volume
   +-- Document registry
   +-- Chat history
   +-- Qdrant container
   +-- Ollama on host machine
```

The backend talks to Qdrant over the Docker network and reaches Ollama through the host machine:

```text
FastAPI -> http://qdrant:6333
FastAPI -> http://host.docker.internal:11434
```

Inside the backend container, `localhost` refers to the backend container itself.

```text
qdrant:6333
-> another Docker service

host.docker.internal:11434
-> Ollama running on the host
```

The Ollama URL and model names should be configurable through environment variables.

## HTTP Server

FastAPI is the main application server.

```text
GET    /docs
POST   /docs
DELETE /docs/{id}

GET    /chat?limit=10&offset=0
POST   /chat
```

The server handles request validation, orchestration, status updates, and responses.

## PDF Upload

The upload request and PDF processing are separate phases.

The browser uploads the PDF to FastAPI using `multipart/form-data`.

```text
Browser
|
| multipart/form-data
v
POST /docs
|
v
FastAPI receives file bytes
|
v
save PDF to mounted storage volume
|
v
create document ID
|
v
add document to registry
|
v
status = processing
|
v
start background processing
|
v
return response
```

The HTTP connection only needs to remain open while the file itself is being transferred and stored. It does not remain open for the full extraction, chunking, embedding, and indexing process.

FastAPI's upload handling can use a file-like upload object rather than requiring the entire PDF to be kept in application memory at once.

Example:

```json
{
  "id": "doc_123",
  "name": "report.pdf",
  "status": "processing"
}
```

## Asynchronous PDF Processing

PDF processing happens after the upload response because ingestion may take time.

```text
PDF
|
v
extract text
|
v
create page-aware chunks
|
v
generate embeddings
|
v
store chunks in Qdrant
|
v
mark document as ready
```

Document states:

```text
processing
ready
failed
deleting
```

For V4, FastAPI background processing is enough.

A later production version could move this work to a dedicated worker or job queue.

## PDF Storage

Uploaded PDFs are stored in a Docker-mounted volume attached to the backend container.

Inside the backend container:

```text
/app/uploads/
├── doc_123.pdf
├── doc_456.pdf
└── ...
```

Conceptually:

```text
Browser
|
v
FastAPI container
|
v
/app/uploads
|
v
Docker volume
```

The volume keeps uploaded PDFs persistent even if the backend container is recreated.

The document registry keeps the relationship between document ID, file name, local path, and processing state.

```json
{
  "id": "doc_123",
  "name": "report.pdf",
  "path": "./uploads/doc_123.pdf",
  "status": "ready",
  "created_at": "..."
}
```

For V4, the registry can remain a JSON file.

## Qdrant

Qdrant runs as its own Docker container and stores retrieval data.

Its storage should also be backed by a Docker volume so vectors and payloads survive container recreation.

Each PDF chunk becomes a Qdrant point:

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

Qdrant is responsible for:

- persistent vector storage
- vector similarity search
- Top-K retrieval
- metadata filtering
- deleting all chunks for a document

The application no longer needs to maintain a separate FAISS index.

The backend reaches Qdrant through the Docker service name:

```text
http://qdrant:6333
```

## Delete PDF

```text
DELETE /docs/{id}
|
v
find document in registry
|
v
mark as deleting
|
v
delete Qdrant points by document_id
|
v
delete local PDF
|
v
remove document from registry
|
v
return success
```

If deletion fails, the document should not be silently removed from the registry.

## Ollama

Ollama runs directly on the host machine rather than inside Docker.

It provides:

```text
qwen3:8b
-> reranking and answer generation

qwen3-embedding:8b
-> document and question embeddings
```

The backend container reaches Ollama through the Docker host gateway:

```text
http://host.docker.internal:11434
```

Example configuration:

```env
OLLAMA_URL=http://host.docker.internal:11434
OLLAMA_CHAT_MODEL=qwen3:8b
OLLAMA_EMBEDDING_MODEL=qwen3-embedding:8b
```

Users can install Ollama separately, pull their preferred models, and configure the backend to use them.

```text
ollama pull qwen3:8b
ollama pull qwen3-embedding:8b
```

Keeping Ollama on the host avoids Docker GPU passthrough setup and lets Ollama use the host GPU directly.

If Ollama is bound only to `127.0.0.1`, the backend container may not be able to reach it depending on the host setup. In that case, Ollama must listen on an interface reachable from Docker while access remains controlled appropriately.

## Synchronous Chat

Chat remains synchronous in V4.

```text
POST /chat
|
v
receive question
|
v
generate question embedding
|
v
search Qdrant
|
v
get Top-K candidates
|
v
relative similarity filtering
|
v
rerank
|
v
select final chunks
|
v
build context
|
v
call LLM
|
v
save chat history
|
v
return answer + citations
```

The frontend waits for the result from the same request.

No polling, WebSockets, or background chat job is required initially.

## Query Response

Example:

```json
{
  "question": "What is ORBIT-18?",
  "answer": "ORBIT-18 is ...",
  "sources": [
    {
      "document_id": "doc_123",
      "document_name": "northstar.pdf",
      "page_start": 4,
      "page_end": 4,
      "chunk_id": 8
    }
  ]
}
```

Citations should come from backend metadata associated with retrieved chunks.

## Chat History

Chat history can initially be stored locally.

```json
[
  {
    "role": "user",
    "content": "What is ORBIT-18?",
    "created_at": "..."
  },
  {
    "role": "assistant",
    "content": "ORBIT-18 is ...",
    "sources": [],
    "created_at": "..."
  }
]
```

Pagination:

```text
GET /chat?limit=10&offset=0
```

The UI can request older messages when the user scrolls upward.

## LLM Context

Full chat history and LLM context are separate.

```text
Full history
-> stored for UI

LLM context
-> recent messages and compacted summary
```

The model input can contain:

```text
system instructions
+
conversation summary if needed
+
recent messages
+
retrieved PDF context
+
current question
```

Retrieved PDF chunks remain the evidence used for grounded answers.

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
├── data/
│   ├── documents.json
│   └── chat_history.json
├── tests/
└── Dockerfile
```

At the project root, Docker Compose orchestrates the backend and Qdrant:

```text
docker-compose.yml
|
+-- backend
+-- qdrant
```

Ollama runs on the host machine.

The Vue UI can remain outside Docker during development and be containerized later if needed for deployment.

The exact structure can evolve while building.

The important separation is:

```text
API layer
|
v
services
|
v
storage / Qdrant / host Ollama
```

## Networking

The backend can call different targets depending on where they run:

```text
Same container
-> localhost

Another Docker service
-> Docker service name
-> example: http://qdrant:6333

Service running on host
-> Docker host gateway
-> example: http://host.docker.internal:11434

External web API
-> normal internet hostname
```

Publishing the FastAPI port allows the host/browser to call the backend. It does not make host services available inside the container through `localhost`.

## Processing Model

```text
PDF ingestion
-> asynchronous/background

Chat
-> synchronous
```

This is intentional.

PDF ingestion may involve many chunks and embedding calls, while chat should remain simple and return the final answer in the same HTTP request.

## Scope

V4 backend does not initially include:

- authentication
- multiple users
- PostgreSQL
- Redis
- Celery
- Kafka
- WebSockets
- token streaming
- distributed workers
- multi-tenant isolation
- advanced monitoring
- direct browser-to-object-storage uploads
- external object storage such as S3

These can be added later when they support a specific learning goal.

## Learning Goal

```text
V3
single Python RAG script
+
FAISS

V4
containerized HTTP application
+
background ingestion
+
Qdrant service
+
host Ollama integration
+
persistent Docker volumes
+
document lifecycle
+
chat API
```

The goal is to understand how a real RAG backend is structured around vector retrieval rather than only how retrieval itself works.
