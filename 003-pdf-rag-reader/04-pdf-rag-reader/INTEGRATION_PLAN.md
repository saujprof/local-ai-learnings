# Integration completion record

All planned units 12.1–12.6 are complete. Backend units 1–11 and real UI
integration are implemented. The sections below preserve the reviewable scopes.

| Unit | Result |
| --- | --- |
| 12.1 HTTP foundation | Axios client, proxy configuration, error handling; HTTP checks and UI build passed |
| 12.2 Documents | Real upload/list/delete, status polling and recovery; live browser flow passed |
| 12.3 Chat/history | Real questions, citations, pagination and reconciliation; browser checks passed |
| 12.4 Runtime | Container connectivity, model dimensions, storage persistence and cleanup passed |
| 12.5 Acceptance | Known-answer/no-evidence checks, recovery and browser checks passed; mobile button fixed |
| 12.6 Completion | Setup, configuration, troubleshooting and limitations documented; final checks passed |

Final validation: **77 backend tests passed**, HTTP client checks passed, and
frontend TypeScript/production build passed. One existing Starlette test-client
deprecation warning remains. Live results are recorded in
[RUNTIME_VERIFICATION.md](RUNTIME_VERIFICATION.md) and
[END_TO_END_VERIFICATION.md](END_TO_END_VERIFICATION.md). Fixture coverage is not
a general model-quality guarantee. Known scope limits are in the root README.

## V4 completion decision — 16 October 2026

V4 and the overall RAG learning system are complete. The later small-model
router classifies casual chat versus RAG, answers GENERAL messages without
document history, and sends document questions through the grounded pipeline.
Its final route benchmark matched all 15 expected routes; 13 of 15 end-to-end
answer checks met their expected behavior.

Two observations remain as optional follow-up work:

- An ambiguous multi-document manager question sometimes retrieves evidence
  from only one PDF. Explicit document selection or document-scope routing can
  be explored in a later version.
- One comparison query repeatedly exceeded the 120-second dependency timeout
  on the available GPU. Stage timing and model-residency optimization can be
  explored when performance becomes the learning goal.

Current retrieval intentionally searches all Ready document IDs, including when
a question names one PDF; semantic search and reranking choose the evidence.
This behavior is accepted for V4's scale.

## 12.1 — HTTP client and development configuration

- Add Axios and a shared client with a configurable API base URL.
- Configure the Vite development proxy to the backend.
- Translate the backend error envelope into useful frontend errors.
- Define timeout behavior for long-running chat and confirmed deletion.
- Keep automatic retries off for mutating requests.

Review: UI builds; HTTP-client checks cover successful responses, empty 204
responses, backend errors, and network failures. Document local and production
API URL setup. Mocks were removed when each feature was switched.

## 12.2 — Real document operations

- Connect list, multipart upload (`file` field), and deletion to the backend.
- Poll while documents are Processing or Deleting; stop on unmount.
- Preserve rows until deletion is confirmed and prevent stale refreshes from
  overwriting completed mutations.
- Add loading/error/retry behavior for initial list and status refresh failures.
- Remove document simulation, filename-triggered failures, and demo labels.

Review: upload a PDF, observe its real status, reload the list, and delete it.
Exercise invalid PDF, processing failure, and failed deletion/retry. Verify that
failed requests do not incorrectly remove documents or report success.

## 12.3 — Real chat and history

- Connect POST /chat and paginated GET /chat to the existing components.
- Remove simulated answers, `/fail` behavior, and local-storage history.
- Preserve Markdown rendering, metadata citations, and history scroll position.
- Distinguish no-ready-document, busy, validation, and dependency errors.
- Provide history refresh/reconciliation after ambiguous POST failures before
  allowing a retry that might duplicate a saved turn.

Review: ask a question, inspect sources, reload saved history, and load older
messages without duplicates or a scroll jump. Failed requests preserve the draft;
network failures do not cause automatic resubmission.

## 12.4 — Runtime and persistence verification

Status: complete; live container, indexing, persistence, and cleanup checks passed. See [runtime results](RUNTIME_VERIFICATION.md).

- Build/start backend and Qdrant with Compose; verify host Ollama connectivity
  and the configured model availability.
- Verify collection creation and actual embedding/vector dimensions.
- Confirm PDFs, registry, history, and vectors survive container recreation.
- Resolve runtime incompatibilities found during these checks.

Review: record actual commands/results. A healthy HTTP server alone does not
prove that the model and vector dependencies work. Retain pending status if the
required services are unavailable; mock tests do not satisfy this unit.

## 12.5 — End-to-end behavior and recovery

Status: complete. See [acceptance results](END_TO_END_VERIFICATION.md).

- Run the real UI → API → Qdrant/Ollama flow with a small known PDF fixture.
- Check factual answers, page citations, and no-evidence responses.
- Exercise deletion during ingestion, interrupted-job recovery, dependency
  failures, and successful cleanup of document vectors.
- Verify browser history pagination, Markdown layout, and status/error states.
- Fix failures and add focused regression tests where they expose missing checks.

Review: upload → Ready → ask → answer/citations → reload/history → delete works.
Document live observations and any remaining limitations. Automated transport
checks and live model-quality review must be reported separately.

## 12.6 — Documentation and completion review

Status: complete. Setup, troubleshooting, verification evidence, and scope
limits are documented; final automated checks passed.

- Remove stale statements that implemented chat/ingestion features are pending.
- Replace mock UI instructions with real setup and review steps.
- Document environment files, ports, model setup, storage, and troubleshooting.
- Confirm backend tests and frontend build pass after the final code changes.
- Summarize completed live checks and explicit outstanding limitations.

Review result: the root README provides the clean-checkout path, and units
12.4–12.5 record the required live checks.

## Order and boundaries

The units were completed in the order 12.1 → 12.2 → 12.3, followed by runtime
and acceptance verification, then documentation review. Vue component blocks
use template → script → style order.
No frontend router/store library, authentication, streaming, or additional
application infrastructure is introduced by this plan. The later model router
is a backend service and does not require a frontend routing library or global
state store.
