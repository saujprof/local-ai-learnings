from contextlib import contextmanager
from threading import Event, Thread
from unittest.mock import Mock

import pytest

from app.config import Settings
from app.services.ingestion_service import IngestionService
from app.services.pdf_service import PDFChunk
from app.storage.repositories import Document, DocumentRepository


def setup(tmp_path):
    settings = Settings(_env_file=None, data_dir=tmp_path / 'data', uploads_dir=tmp_path / 'uploads')
    settings.uploads_dir.mkdir()
    path = settings.uploads_dir / 'doc.pdf'
    path.write_bytes(b'fixture')
    repo = DocumentRepository(settings.data_dir)
    repo.add(Document(id='doc', name='file.pdf', path=str(path), status='processing', created_at='now'))
    embeddings, vectors = Mock(), Mock()
    embeddings.embed.return_value = [[1, 2]]
    @contextmanager
    def clients(_):
        yield embeddings, vectors
    processor = Mock(return_value=[PDFChunk('doc', 'file.pdf', 0, 1, 1, 'text')])
    return IngestionService(settings, repo, clients, processor), repo, embeddings, vectors, path


def test_ready_and_delete(tmp_path):
    service, repo, embeddings, vectors, path = setup(tmp_path)
    service.ingest('doc')
    assert repo.get('doc')['status'] == 'ready'
    vectors.upsert.assert_called_once()
    service.delete('doc')
    assert repo.get('doc') is None and not path.exists()


def test_failure_cleans_partial_vectors(tmp_path):
    service, repo, _, vectors, _ = setup(tmp_path)
    vectors.upsert.side_effect = RuntimeError('private')
    service.ingest('doc')
    assert repo.get('doc')['status'] == 'failed'
    assert 'private' not in repo.get('doc')['error']
    assert vectors.delete_document.call_count == 2


def test_cleanup_failure_is_retryable(tmp_path):
    service, repo, _, vectors, path = setup(tmp_path)
    vectors.delete_document.side_effect = RuntimeError('offline')
    with pytest.raises(RuntimeError):
        service.delete('doc')
    assert repo.get('doc')['status'] == 'failed' and path.exists()
    vectors.delete_document.side_effect = None
    service.delete('doc')
    assert repo.get('doc') is None


def test_delete_during_embedding(tmp_path):
    service, repo, embeddings, vectors, path = setup(tmp_path)
    started, release = Event(), Event()
    def embed(_):
        started.set()
        assert release.wait(5)
        return [[1, 2]]
    embeddings.embed.side_effect = embed
    ingestion = Thread(target=service.ingest, args=('doc',))
    ingestion.start()
    assert started.wait(5)
    deletion = Thread(target=service.delete, args=('doc',))
    deletion.start()
    release.set()
    ingestion.join(5)
    deletion.join(5)
    assert not ingestion.is_alive() and not deletion.is_alive()
    assert repo.get('doc') is None and not path.exists()
    assert vectors.mock_calls[-1][0] == 'delete_document'


def test_restart_marks_interrupted_records(tmp_path):
    service, repo, _, _, _ = setup(tmp_path)
    service.recover()
    assert repo.get('doc')['status'] == 'failed'
    assert 'restart' in repo.get('doc')['error']
    repo.set_status('doc', 'deleting')
    service.recover()
    assert repo.get('doc')['status'] == 'failed'
