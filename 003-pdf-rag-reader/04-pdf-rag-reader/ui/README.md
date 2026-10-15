# V4 UI - PDF RAG Chat

Implementation record: [Unit 12 integration plan](../INTEGRATION_PLAN.md).

The V4 frontend is a simple Vue 3 interface for uploading PDFs, managing indexed documents, asking questions, and viewing answers with citations.

The UI should stay intentionally simple so the main learning remains focused on the RAG system.

## Stack

```text
Vue 3
```

The existing scaffold uses TypeScript and Vite. Start without Vue Router or
Pinia: this is one screen, with shared state in `App.vue` and composables when
needed. Keep service calls in `src/services/api.ts`.

## Implementation Units

All five units are implemented; the list records their original sequence:

1. **Screen layout:** Documents and Chat panels, empty states, responsive layout.
2. **Document interactions:** typed document models, API service, PDF upload,
   processing states, and deletion after service confirmation.
3. **Chat interactions:** question input, backend responses, waiting state, answers,
   and separate source citations.
4. **Chat history:** initial history, loading older messages, and preserving the
   reader's scroll position when prepending messages.
5. **Backend integration:** agree on response shapes, connect HTTP endpoints,
   poll document status, and handle API failures with useful recovery actions.

Current implementation: document operations, chat, and history use the real
backend. Runtime and browser acceptance checks also passed.

### Reviewing real document operations (12.2)

Start the backend and UI using the HTTP foundation instructions below.

- Upload a nonempty PDF. The UI sends multipart field `file` to POST /docs.
- Observe Processing followed by Ready or Failed from the backend. Processing
  requires the backend's Ollama and Qdrant dependencies.
- Reload or use Refresh documents to load persisted documents.
- Delete a document. Its row remains Deleting until the API confirms deletion.
- Stop the backend to check list/refresh errors, then restart it and use Refresh
  documents to retry. Polling pauses on a refresh failure.
- After an upload timeout, refresh before uploading again: the first upload may
  already have been saved. A failed deletion keeps its row; refresh to reconcile
  the backend state before retrying.

Status polling runs every three seconds while any document is Processing or
Deleting and stops on unmount. Concurrent refreshes are suppressed; responses
started before a completed mutation cannot overwrite it. Upload filename/empty
checks are preliminary; PDF validation is backend-owned. `.fail.pdf` no longer
has special behavior. Live lifecycle checks passed; see the root verification reports.

### Reviewing real chat and history (12.3)

Chat now uses POST /chat and paginated GET /chat. No simulated answers,
filename triggers, `/fail` commands, or browser-stored history remain in the
service. Old `pdf-rag-demo-chat-v1` browser data is ignored.

- Upload a PDF and wait until Ready, then send a question.
- Verify Markdown answers and backend-owned PDF/page citations.
- Reload to retrieve persisted messages. Scroll upward to load older pages.
- Use Refresh history to replace the conversation with the latest ten stored
  messages and reset pagination. This does not clear the draft.
- Backend errors are displayed using their message. Failed sends retain the
  draft and remove the temporary question from the conversation.
- A network failure or server error blocks sending until history refresh succeeds.
  Inspect the refreshed conversation before retrying. A refresh is a snapshot:
  the original request may still be processing, so it cannot guarantee that a
  retry will never duplicate a turn. Requests are never automatically resent.
- Initial/older-history failures support retry. The backend limits questions to
  10,000 characters; the input enforces the same limit.

Successful sends use temporary UI message IDs until history is refreshed; offset
advances by the two persisted messages. Backend IDs are used for loaded history.
Browser scroll behavior and the live fixture answer/citation checks passed in unit 12.5.

## Local Development

From this `ui` directory:

```sh
npm ci
npm run dev
```

Run `npm run build` to type-check and produce the production bundle.

## Main Screen

```text
------------------------------------------------
Documents
------------------------------------------------
[ Upload PDF ]

report.pdf              Ready       Delete
policy.pdf              Processing  Delete
manual.pdf              Ready       Delete

------------------------------------------------
Chat
------------------------------------------------

User:
What is the refund policy?

Assistant:
The refund policy states ...

Sources:
policy.pdf - Page 7

------------------------------------------------
[ Ask a question...                         ]
[ Send ]
------------------------------------------------
```

## Main Features

- upload PDF
- show uploaded PDF list
- show document processing status
- delete PDF
- basic chat interface
- send questions
- show loading state while waiting
- show answer
- show PDF/page citations
- load previous chat messages
- load older messages when the user scrolls upward

## Suggested Structure

```text
frontend/
├── src/
│   ├── components/
│   │   ├── DocumentUpload.vue
│   │   ├── DocumentList.vue
│   │   ├── ChatMessage.vue
│   │   ├── ChatWindow.vue
│   │   ├── QuestionInput.vue
│   │   └── SourceList.vue
│   ├── services/
│   │   └── api.js
│   ├── App.vue
│   └── main.js
└── README.md
```

## Document Upload Flow

```text
User clicks Upload
↓
selects PDF
↓
POST /docs
↓
backend returns document with status=processing
↓
UI adds document to list
↓
UI refreshes document status
↓
processing → ready
```

Simple polling is acceptable for document status.

Example:

```text
GET /docs
```

every few seconds while at least one document is still processing.

## Document List

Each row should show:

```text
document name
status
delete action
```

Possible states:

```text
Processing
Ready
Failed
Deleting
```

## Delete Flow

```text
User clicks Delete
↓
DELETE /docs/{id}
↓
show deleting state
↓
backend completes deletion
↓
remove document from UI
```

The UI should not assume deletion succeeded before the backend confirms it.

## Chat Flow

For the first V4 implementation, chat remains synchronous.

```text
User types question
↓
POST /chat
↓
show loading state
↓
backend performs RAG
↓
response arrives
↓
show answer + citations
```

Example response:

```json
{
  "question": "What is ORBIT-18?",
  "answer": "ORBIT-18 is ...",
  "sources": [
    {
      "document_name": "northstar.pdf",
      "page_start": 4,
      "page_end": 4
    }
  ]
}
```

## Citations

Sources should be rendered separately from the answer.

```text
Answer:
ORBIT-18 is the next planned phase ...

Sources:
northstar.pdf - Page 4
northstar.pdf - Pages 5-6
```

The frontend should display citation metadata returned by the backend rather than trying to extract it from the answer text.

## Chat History

Initial load:

```text
GET /chat?limit=10&offset=0
```

When the user scrolls upward:

```text
GET /chat?limit=10&offset=10
GET /chat?limit=10&offset=20
```

Older messages are inserted above the current conversation.

The frontend does not need to poll chat every two seconds because `POST /chat` returns the completed answer.

## Basic UI States

The UI should handle:

```text
uploading PDF
processing PDF
failed PDF processing
deleting PDF
sending question
waiting for answer
API failure
empty document list
empty chat
```

No complex design system is required for V4.

## API Usage

```text
GET    /docs
POST   /docs
DELETE /docs/{id}

GET    /chat?limit=10&offset=0
POST   /chat
```

Keep backend calls in:

```text
services/api.js
```

so Vue components stay focused on UI behavior.

## Scope

V4 UI is intentionally not focused on:

- authentication
- multiple users
- advanced routing
- WebSockets
- token streaming
- rich PDF preview
- complex design system
- admin dashboards

The purpose of this UI is to make the RAG backend usable as a complete application.

## HTTP foundation (integration unit 12.1)

Axios is configured in `src/services/http.ts`. Document features now use this client; chat and history also use this client. `ApiError` retains the backend's message,
code, and HTTP status. Network failures on mutations are flagged `ambiguous` so
later integration can reconcile state before retrying. Requests are never retried
automatically. The default timeout is five minutes; callers can override it.
A timeout does not cancel processing already started on the backend.

Copy `.env.example` to `.env.local` if needed, then restart Vite. `/api` requests
are proxied to `API_PROXY_TARGET` (default `http://127.0.0.1:8000`), stripping the
prefix. This keeps development browser requests on the UI origin.

For production, configure a reverse proxy for `/api`, or build with an absolute
`VITE_API_BASE_URL` and configure matching backend CORS. The Vite development
proxy is not a production deployment proxy. Never put secrets in VITE_ variables.

Run `npm run test:http` with Node 22.18+ (native TypeScript stripping), and
`npm run build` for TypeScript/build validation.
