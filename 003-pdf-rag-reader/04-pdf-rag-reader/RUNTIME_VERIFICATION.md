# Unit 12.4 runtime verification

Status: complete. Live checks passed after Docker became available.

- Built the backend image and started backend/Qdrant with Compose.
- Backend health check passed. Backend container reached Qdrant and host Ollama;
  both configured models were present.
- Uploaded a generated one-page text PDF via POST /docs. Background ingestion
  reached Ready and stored document vectors in a 4,096-dimensional collection.
- Recreated both containers using `docker compose up -d --force-recreate`.
  The PDF, Ready registry record, and document vectors survived recreation.
- Saved an isolated two-message ChatRepository fixture in the backend data volume;
  both messages survived recreation. Existing API history remained unchanged.
- Deleted the disposable document through DELETE /docs (204). Verified its PDF
  was gone and the document-filtered Qdrant point count was zero.
- Removed the isolated history fixture and verification marker. Existing user
  documents/history were not removed. Containers remain running.

Commands used included `docker compose up --build -d`,
`docker compose exec -T backend python -m scripts.check_connections`, and
`docker compose up -d --force-recreate`. Fixture checks ran inside the backend
container using its actual Settings, repository code, HTTP API, and Qdrant REST
API. These were live checks, not mocked transports.

Unit 12.5 still covers browser behavior, generated-answer quality, citation
accuracy, and live failure/recovery scenarios. The history persistence check here
used an isolated repository fixture, not a generated chat answer.
