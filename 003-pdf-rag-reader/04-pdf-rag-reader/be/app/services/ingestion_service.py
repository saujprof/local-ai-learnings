"""Single-worker lifecycle coordination for ingestion and confirmed deletion."""
import logging
from pathlib import Path
from threading import Lock

from app.errors import APIError
from app.services.pdf_service import PDFProcessingError, process_pdf
from app.services.vector_clients import vector_clients

logger = logging.getLogger(__name__)


class IngestionService:
    def __init__(self, settings, repository, clients=vector_clients, processor=process_pdf):
        self.settings, self.repository = settings, repository
        self.clients, self.processor = clients, processor
        # Serialize ingestion and vector cleanup: avoids collection-creation races
        # and guarantees no writes from ingestion after confirmed deletion.
        self.work_lock = Lock()

    def recover(self):
        for record in self.repository.list():
            if record['status'] in ('processing', 'deleting'):
                self.repository.set_status(record['id'], 'failed',
                    'Operation interrupted by restart. Delete this document to clean up, then upload again.')

    def ingest(self, document_id):
        with self.work_lock:
            record = self.repository.get(document_id)
            if not record or record['status'] != 'processing':
                return
            try:
                chunks = self.processor(Path(record['path']), record['id'], record['name'])
                with self.clients(self.settings) as (embeddings, vectors):
                    vectors.delete_document(document_id)
                    for start in range(0, len(chunks), self.settings.embedding_batch_size):
                        current = self.repository.get(document_id)
                        if not current or current['status'] != 'processing':
                            return  # deletion waiting on work_lock performs cleanup
                        batch = chunks[start:start + self.settings.embedding_batch_size]
                        vectors.upsert(batch, embeddings.embed([chunk.text for chunk in batch]))
                with self.repository.store.lock:
                    current = self.repository.get(document_id)
                    if current and current['status'] == 'processing':
                        self.repository.set_status(document_id, 'ready')
            except Exception as exc:
                logger.exception('Document ingestion failed: %s', document_id)
                message = exc.message if isinstance(exc, APIError) else (
                    str(exc) if isinstance(exc, PDFProcessingError) else 'PDF processing failed. Delete and upload again.')
                try:
                    with self.clients(self.settings) as (_, vectors):
                        vectors.delete_document(document_id)
                except Exception:
                    logger.exception('Partial vector cleanup failed: %s', document_id)
                    message += ' Vector cleanup is pending; retry deleting the document.'
                with self.repository.store.lock:
                    current = self.repository.get(document_id)
                    if current and current['status'] == 'processing':
                        self.repository.set_status(document_id, 'failed', message)

    def delete(self, document_id):
        with self.repository.store.lock:
            record = self.repository.get(document_id)
            if record is None:
                raise APIError(404, 'document_not_found', 'Document not found.')
            if record['status'] == 'deleting':
                raise APIError(409, 'document_deleting', 'Document is already being deleted.')
            self.repository.set_status(document_id, 'deleting')
        with self.work_lock:
            try:
                with self.clients(self.settings) as (_, vectors):
                    vectors.delete_document(document_id)
                path = Path(record['path']).resolve()
                if path.parent != self.settings.uploads_dir.resolve():
                    raise ValueError('Stored file is outside the upload directory')
                path.unlink(missing_ok=True)
                self.repository.remove(document_id)
            except Exception:
                self.repository.set_status(document_id, 'failed', 'Deletion failed. Try again to finish cleanup.')
                raise
