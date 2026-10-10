# V4 API contract

This is the contract for the first backend implementation. Document lifecycle and chat/history routes are implemented. Live end-to-end
verification and UI integration remain pending. GET /health is implemented as a liveness endpoint returning
200 with `{"status":"ok"}`. Paths have no API prefix; deployment proxies may add one.
JSON field names are case-sensitive. IDs are opaque strings. Timestamps, when
present, are UTC ISO 8601 strings. No authentication is required in V4.

Interactive API documentation will be served at `/api-docs`, with OpenAPI at
`/openapi.json`, leaving `/docs` available for document operations.

## Documents

A public document contains `id`, `name`, and `status`. `status` is one of
`processing`, `ready`, `failed`, or `deleting`. Optional `error` contains a
user-readable processing/deletion failure. Internal filesystem paths are never
returned. Names are display names; storage uses generated IDs.

```json
{"id":"doc_123","name":"report.pdf","status":"processing"}
```

### GET /docs

Returns **200**, a JSON array (no envelope), newest documents first. An empty
registry returns `[]`. Includes processing, failed, and deleting documents.

```json
[
  {"id":"doc_456","name":"manual.pdf","status":"failed","error":"No extractable text found."},
  {"id":"doc_123","name":"report.pdf","status":"ready"}
]
```

### POST /docs

Request: `multipart/form-data` with exactly one file field named `file`.
The client lets the browser supply the multipart boundary. Each accepted upload
gets a new ID, even when its filename matches an existing document.

Returns **202 Accepted**, a public document with `status: "processing"`, only
after the file and registry entry have been saved. Ingestion starts in the
background. Clients poll GET /docs to observe Ready or Failed.

Reject an empty or invalid PDF with **400**, a request exceeding the configured
upload limit with **413**, an unsupported file type with **415**, and a missing
file field with **422**. Extension/MIME checks alone do not establish a valid
PDF; the backend validates content. Extraction failures discovered later change
the document to Failed and set `error` rather than changing the upload response.

### DELETE /docs/{id}

No request body. Deletion completes within the request: mark Deleting, stop or
coordinate any ingestion, remove all document vectors, delete the PDF, and
remove the registry entry. Return **204 No Content** only after completion.

Unknown ID: **404**. An already-running deletion: **409**. Dependency failure:
**503**. Other unexpected failure: **500**. On failure, retain the registry
entry, mark Failed with an explanatory `error`, and permit another deletion
attempt. Cleanup must tolerate already-removed vectors/files on retry.

The UI keeps the row until 204. If the response is lost, refreshing GET /docs
reconciles whether deletion completed. A processing job must never recreate
vectors after deletion completes.

## Chat

### Sources

```json
{"document_id":"doc_123","document_name":"report.pdf","page_start":4,"page_end":5,"chunk_id":8}
```

Required: `document_id`, `document_name`, `page_start`, `page_end`.
Page numbers are positive, one-based integers; `page_end >= page_start`.
`chunk_id` is optional metadata. Sources come from selected evidence metadata,
not parsing generated answer text. Historical sources remain even if a document
is subsequently deleted. No PDF preview URL is promised.

### POST /chat

Request: `application/json`.

```json
{"question":"What is the refund policy?"}
```

`question` is required, must be a string, and must not be blank after trimming.
Questions are limited to 10,000 characters. Invalid input returns **422**. The backend trims the question. Only one chat
request runs at a time in this single-conversation V4 app; another concurrent
request returns **409** rather than interleaving history turns.

Returns **200** after retrieval, answer generation, and persistence of both
messages:

```json
{
  "question":"What is the refund policy?",
  "answer":"Refunds are available within **30 days**.",
  "sources":[{"document_id":"doc_123","document_name":"report.pdf","page_start":4,"page_end":4,"chunk_id":8}]
}
```

`answer` is Markdown text, not HTML. `sources` is always an array. No ready
documents returns **409**. Ready documents but insufficient evidence returns
**200** with an explanatory answer and `sources: []`; it must not fabricate an
answer. Dependency unavailability returns **503**, dependency timeout **504**,
and unexpected failures **500**. Failed turns are not partially persisted.

The response shape matches the current UI. Persisted messages receive stable
backend IDs, exposed through GET /chat. Clients may use temporary IDs for the
immediate response. Do not automatically retry POST requests after ambiguous
network failures: refresh history first, since a turn may already have saved.

### GET /chat?limit=10&offset=0

`limit`: integer, default 10, range 1–100. `offset`: integer, default 0,
minimum 0. Invalid pagination returns **422**.

Offsets count individual messages from the newest end of history, not turns.
Each page is returned oldest to newest. Offset past the end returns an empty
page with `hasMore: false`. Pages may split a question/answer pair.

```json
{
  "messages":[
    {"id":"msg_1","role":"user","content":"What is the refund policy?","created_at":"2026-10-03T09:00:00Z"},
    {"id":"msg_2","role":"assistant","content":"Refunds are available within **30 days**.","sources":[{"document_id":"doc_123","document_name":"report.pdf","page_start":4,"page_end":4}],"created_at":"2026-10-03T09:00:01Z"}
  ],
  "hasMore":false
}
```

Messages require stable unique `id`, `role` (`user` or `assistant`), `content`,
and `created_at`. Assistant messages include `sources` (possibly empty); user
messages omit it. IDs and insertion order must survive restarts. Timestamps are
metadata, not the ordering key. Empty history returns
`{"messages":[],"hasMore":false}`.

Example with 24 stored messages: offset 0 returns messages 15–24, offset 10
returns 5–14, offset 20 returns 1–4. After the client saves a new turn, it adds
two to its pagination offset before requesting older messages. This offset
scheme assumes one active UI session; concurrent tabs are outside V4 scope.

## Errors

All API errors, including validation and unexpected errors, use the same JSON
envelope. Do not return internal traces or filesystem paths.

```json
{"error":{"code":"document_not_found","message":"Document not found."}}
```

`code` is a stable machine-readable string; `message` is user-readable.
The future HTTP adapter extracts `error.message` and throws an Error for the
existing composables. Do not rely on FastAPI's default validation envelope.

| Status | Example codes |
| --- | --- |
| 400 | `invalid_pdf` |
| 404 | `document_not_found` |
| 409 | `document_deleting`, `no_ready_documents`, `chat_busy` |
| 413 | `upload_too_large` |
| 415 | `unsupported_file_type` |
| 422 | `validation_error` |
| 500 | `internal_error` |
| 503 | `dependency_unavailable` |
| 504 | `dependency_timeout` |

## UI compatibility and implementation checklist

- `PdfDocument` already matches the public document schema.
- `ChatResponse` matches POST /chat; the UI may ignore optional `chunk_id`.
- `ChatHistoryPage` matches the history envelope and pagination semantics.
- The UI's `ChatMessage` can ignore the additional `created_at` field.
- Unit 2 should configure the documentation path; subsequent units implement
  validation and error handlers to this contract.
- Unit 12 replaces the mock service with Axios. Keep both unit 12 and live
  integration verification pending until the backend is implemented.
