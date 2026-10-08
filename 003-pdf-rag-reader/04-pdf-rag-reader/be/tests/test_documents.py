from io import BytesIO
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient
from pypdf import PdfWriter

from app.config import Settings
from app.main import create_app


def pdf():
    output = BytesIO()
    writer = PdfWriter()
    writer.add_blank_page(width=100, height=100)
    writer.write(output)
    return output.getvalue()


def settings(tmp_path, **kwargs):
    return Settings(_env_file=None, data_dir=tmp_path / 'data', uploads_dir=tmp_path / 'uploads', **kwargs)


def test_upload_restart_delete(tmp_path):
    config = settings(tmp_path)
    with TestClient(create_app(config)) as client:
        assert client.get('/docs').json() == []
        response = client.post('/docs', files={'file': ('../report.pdf', pdf(), 'application/pdf')})
        assert response.status_code == 202
        record = response.json()
        assert record['name'] == 'report.pdf'
        assert record['status'] == 'processing'
        assert 'path' not in record
        second = client.post('/docs', files={'file': ('report.pdf', pdf())}).json()
        assert second['id'] != record['id']
    with TestClient(create_app(config)) as client:
        assert len(client.get('/docs').json()) == 2
        response = client.delete('/docs/' + record['id'])
        assert response.status_code == 204 and response.content == b''
        assert not (config.uploads_dir / f"{record['id']}.pdf").exists()
        assert client.delete('/docs/' + record['id']).status_code == 404


def test_reject_uploads(tmp_path):
    with TestClient(create_app(settings(tmp_path, max_upload_bytes=1024))) as client:
        assert client.post('/docs').status_code == 422
        for name, content, status in [('x.txt', b'text', 415), ('x.pdf', b'', 400),
                                      ('x.pdf', b'%PDF-not-a-pdf', 400), ('x.pdf', b'x' * 1025, 413)]:
            response = client.post('/docs', files={'file': (name, content)})
            assert response.status_code == status
            assert 'error' in response.json()
        assert client.get('/docs').json() == []
        assert list((tmp_path / 'uploads').iterdir()) == []


def test_delete_failure_is_retained_and_retryable(tmp_path):
    app = create_app(settings(tmp_path))
    with TestClient(app, raise_server_exceptions=False) as client:
        record = client.post('/docs', files={'file': ('x.pdf', pdf())}).json()
        original = Path.unlink
        def fail_pdf(path, *args, **kwargs):
            if path.suffix == '.pdf':
                raise PermissionError('private details')
            return original(path, *args, **kwargs)
        with patch.object(Path, 'unlink', fail_pdf):
            response = client.delete('/docs/' + record['id'])
        assert response.status_code == 500
        assert 'private details' not in response.text
        assert client.get('/docs').json()[0]['status'] == 'failed'
        assert client.delete('/docs/' + record['id']).status_code == 204
