# V4 UI - PDF RAG Chat

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

Implement and review one unit at a time:

1. **Screen layout:** Documents and Chat panels, empty states, responsive layout.
2. **Document interactions:** typed document models, mock service, PDF upload,
   processing states, and deletion after service confirmation.
3. **Chat interactions:** question input, mock responses, waiting state, answers,
   and separate source citations.
4. **Chat history:** initial history, loading older messages, and preserving the
   reader's scroll position when prepending messages.
5. **Backend integration:** agree on response shapes, connect HTTP endpoints,
   poll document status, and handle API failures with useful recovery actions.

Current progress: units 1–4 are implemented. Documents and chat use an in-memory
mock service. Chat history persists in browser local storage. No PDF content is uploaded or indexed
yet, and reloading the page clears the mock documents.

### Reviewing Unit 2

- Select a nonempty `.pdf` file. It appears as Processing, then Ready after
  approximately three seconds plus the next status refresh.
- Select a file named `example.fail.pdf` to simulate failed processing.
- Delete a document in any state. It remains visible as Deleting until the mock
  service confirms deletion.
- Try an empty PDF or a non-PDF file (if the file picker allows it) to see a
  validation error. The filename check is only preliminary UI validation;
  actual PDF validation belongs to the backend.
- Upload the same file again to confirm each upload gets its own document ID.
- Reload the page to return to the empty state.

The mock API lives in `src/services/api.ts`; document state and refresh cleanup
live in `src/composables/useDocuments.ts`. No router or store library is needed.

### Reviewing Unit 3

- Upload a PDF and wait for Ready. Question input is disabled until a document
  is ready, and blank questions cannot be sent.
- Send a question. Your message appears immediately, followed by a waiting
  indicator and then a clearly labeled demo answer with separate sources.
- Upload two PDFs to see both single-page and page-range citation formatting.
  Page numbers are simulated; the mock service does not read PDF content.
- Submit `/fail` to simulate a chat error. The draft remains available to edit
  and resend; the failed turn is removed from the conversation.
- While waiting, input and Send are disabled to prevent duplicate requests.
- New messages scroll into view when you are near the bottom; reading older
  messages keeps your position. Chat history survives reloads.

Chat state lives in `src/composables/useChat.ts`, with typed responses and sources
in `src/types/chat.ts`. `ChatWindow`, `ChatMessage`, `SourceList`, and
`QuestionInput` handle presentation. Assistant answers render Markdown through `markdown-it` and are sanitized with
DOMPurify. User questions remain plain text; citations stay separate. Headings,
lists, tables, links, blockquotes, and fenced code blocks are supported. Raw HTML
and image rendering are disabled. Code blocks do not yet have syntax highlighting.

### Reviewing Unit 4

- Send at least six questions to create more than ten messages, then reload.
  The latest ten messages load in chronological order, scrolled to the bottom.
- Scroll to the top or select **Load older messages**. Older messages are
  prepended while preserving the visible message position.
- Continue until **Beginning of conversation** appears. Sending another question
  updates the history offset so older pages do not repeat the new turn.
- History loading and errors have separate states; use **Retry history** after
  a storage failure. Sending pauses during history requests.
- Mock history uses local storage key `pdf-rag-demo-chat-v1`. Clear that key in
  browser developer tools to reset the conversation. PDFs still clear on reload,
  so upload again before sending new questions. Old citations remain historical.

The mock history endpoint uses message-based `limit` and `offset` (not turns),
with offsets counted from newest, each returned page ordered oldest to newest,
plus `hasMore`. This contract must be agreed with the backend in unit 5.
Concurrent tabs are outside this mock's scope.

## Local Development

From this `ui` directory:

```sh
npm install
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
