# Remaining integration work

Backend units 1–11 and the mock UI are implemented. Split unit 12 into the
following reviewable units. Unit 12.1 is implemented and its HTTP checks and UI build pass. Unit 12.2 implementation is complete; live document lifecycle review remains pending. Unit 12.3 implementation is complete; live chat/history review remains pending. Unit 12.4 live verification is complete. Units 12.5–12.6 are pending. Implement and review
one unit at a time; update documentation alongside each change.

## 12.1 — HTTP client and development configuration

- Add Axios and a shared client with a configurable API base URL.
- Configure the Vite development proxy to the backend.
- Translate the backend error envelope into useful frontend errors.
- Define timeout behavior for long-running chat and confirmed deletion.
- Keep automatic retries off for mutating requests.

Review: UI builds; HTTP-client checks cover successful responses, empty 204
responses, backend errors, and network failures. Document local and production
API URL setup. Existing mocks remain usable until each feature is switched.

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

- Remove stale statements that implemented chat/ingestion features are pending.
- Replace mock UI instructions with real setup and review steps.
- Document environment files, ports, model setup, storage, and troubleshooting.
- Confirm backend tests and frontend build pass after the final code changes.
- Summarize completed live checks and explicit outstanding limitations.

Review: a reader can follow the documented setup from a clean checkout. Mark
unit 12 complete only after implementation and required live checks are done.

## Order and boundaries

Implement 12.1 → 12.2 → 12.3. Runtime verification (12.4) may start earlier when
Docker and Ollama are available; it must pass before live acceptance in 12.5.
Finish with 12.6. Keep Vue component blocks in template → script → style order.
No router/store library, authentication, streaming, or additional backend feature
units are introduced by this plan.
