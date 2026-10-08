"""Local document lifecycle; background ingestion is connected in unit 8."""
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, File, Request, Response, UploadFile
from pypdf import PdfReader

from app.errors import APIError
from app.storage.repositories import Document

router = APIRouter(tags=['documents'])


def public(record: dict) -> dict:
    return {key: record[key] for key in ('id', 'name', 'status', 'error') if key in record}


@router.get('/docs')
def list_documents(request: Request):
    return [public(record) for record in request.app.state.documents.list()]


@router.post('/docs', status_code=202)
def upload_document(request: Request, file: UploadFile = File(...)):
    settings = request.app.state.settings
    repository = request.app.state.documents
    name = (file.filename or '').replace('\\', '/').rsplit('/', 1)[-1]
    destination = None
    saved = False
    try:
        if not name.lower().endswith('.pdf'):
            raise APIError(415, 'unsupported_file_type', 'Choose a PDF file.')
        settings.uploads_dir.mkdir(parents=True, exist_ok=True)
        document_id = str(uuid4())
        destination = settings.uploads_dir.resolve() / f'{document_id}.pdf'
        size = 0
        with destination.open('xb') as output:
            while chunk := file.file.read(64 * 1024):
                size += len(chunk)
                if size > settings.max_upload_bytes:
                    raise APIError(413, 'upload_too_large', 'PDF exceeds the configured upload limit.')
                output.write(chunk)
        if size == 0:
            raise APIError(400, 'invalid_pdf', 'The PDF is empty.')
        try:
            with destination.open('rb') as content:
                if content.read(5) != b'%PDF-':
                    raise ValueError('Missing PDF header')
                content.seek(0)
                reader = PdfReader(content)
                if reader.is_encrypted or not len(reader.pages):
                    raise ValueError('Encrypted or empty PDF')
        except Exception as exc:
            raise APIError(400, 'invalid_pdf', 'Choose a readable, unencrypted PDF with at least one page.') from exc
        record = repository.add(Document(
            id=document_id, name=name, path=str(destination), status='processing',
            created_at=datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
        ))
        saved = True
        return public(record)
    finally:
        file.file.close()
        if destination is not None and not saved:
            destination.unlink(missing_ok=True)


@router.delete('/docs/{document_id}', status_code=204)
def delete_document(document_id: str, request: Request):
    repository = request.app.state.documents
    # Single-process lock protects the whole local deletion transaction.
    with repository.store.lock:
        record = repository.get(document_id)
        if record is None:
            raise APIError(404, 'document_not_found', 'Document not found.')
        if record['status'] == 'deleting':
            raise APIError(409, 'document_deleting', 'Document is already being deleted.')
        repository.set_status(document_id, 'deleting')
        try:
            path = Path(record['path']).resolve()
            if path.parent != request.app.state.settings.uploads_dir.resolve():
                raise ValueError('Stored file is outside the upload directory')
            path.unlink(missing_ok=True)
            repository.remove(document_id)
        except Exception:
            repository.set_status(document_id, 'failed', 'Deletion failed. Try again.')
            raise
    return Response(status_code=204)
