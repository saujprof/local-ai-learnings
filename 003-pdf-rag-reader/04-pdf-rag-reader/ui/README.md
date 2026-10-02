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

Current progress: unit 1 is implemented. Upload and chat controls arrive in
units 2 and 3; the current screen only shows the layout and empty states.

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
