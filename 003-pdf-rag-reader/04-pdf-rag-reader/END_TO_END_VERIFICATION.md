# Unit 12.5 acceptance results

Status: complete for the planned acceptance checks.

## Live backend checks — passed

Checks used a temporary backend process inside the running container with isolated
JSON/PDF directories and a disposable Qdrant collection. The real Ollama models
were used. Existing user documents and chat history were untouched.

- Generated a one-page PDF stating that the ORBIT-42 policy allows refunds within
  30 days. Upload reached Ready through real extraction, embedding, and indexing.
- Asked how many days refunds are allowed. The answer stated 30 days and cited
  `acceptance.pdf`, page 1, using the correct document ID and chunk metadata.
- Asked about the capital of fictional ZENTORIA. The response used the fixed
  no-evidence answer and returned no sources.
- Paginated the two completed turns in pages of two messages; restarted the
  isolated backend and verified the saved message IDs were unchanged.
- Uploaded another fixture and immediately deleted it while ingestion was
  scheduled/active. Deletion completed successfully.
- Deleted the original document; Qdrant exact point count became zero.
- Restarted the isolated backend with an unreachable Ollama URL. Upload reached
  Failed with an error and could subsequently be deleted successfully.
- Started a fresh backend with Processing and Deleting registry records left by
  an interrupted operation. GET /docs returned Failed with restart guidance.
- Deleted the disposable Qdrant collection. Temporary filesystem fixtures remain
  only inside the container's temporary directory, not application data volumes.

The frontend production build also passed. These results establish the tested
fixture behavior; they do not establish answer quality for arbitrary documents.

## Browser acceptance — live Chromium checks

Browser tests used a separate backend container on port 8002 with temporary
storage and a disposable Qdrant collection, reached through the real Vite proxy
on port 5174. They used the actual frontend, backend, Qdrant, and Ollama for the
upload/question flow.

Passed:

- Browser PDF selection/upload, visible Processing → Ready transition.
- Real question submission and waiting state; answer stated 30 days and showed
  a page-1 citation. Reload restored the two saved messages.
- Browser deletion removed the document after confirmation.
- Seeded history fixtures loaded ten messages initially; scrolling upward added
  older messages with unique IDs and preserved the visible anchor position.
- Bold text, tables, and fenced code rendered correctly. Embedded script text
  remained text rather than executable DOM.
- Injected browser network failure displayed a document refresh error; retry
  succeeded after the connection was restored.
- Initial history-load failure displayed Retry history; retry loaded messages.
- Injected chat-send failure retained the draft, blocked sending until successful
  history reconciliation, and did not automatically resend the question.
- Mobile layout at 390px had no horizontal page overflow. Screenshot review
  found the Send button wrapping vertically; CSS now prevents shrinking/wrapping.
  Repeated browser checks and screenshot inspection passed after the fix.

Layout/history fixtures were seeded into the isolated backend to exercise these
states efficiently; they are not model-generated answers. Network failures were
injected by the browser tool. Earlier backend recovery checks used real service
configuration failures. These distinctions matter when interpreting coverage.

The frontend build passed after the mobile fix. Temporary browser tools and
screenshots are outside the repository under `/tmp/rag-browser`.

The disposable browser backend and Qdrant collection were cleaned up after the
checks; the main application containers and user data were preserved.
