import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.config import Settings
from app.main import APIError, create_app


def test_health_and_documentation():
    with TestClient(create_app(Settings(_env_file=None))) as client:
        assert client.get('/health').json() == {'status': 'ok'}
        assert client.get('/health').status_code == 200
        assert client.get('/api-docs').status_code == 200
        assert '/health' in client.get('/openapi.json').json()['paths']
        assert client.get('/missing').status_code == 404
        assert client.get('/missing').json()['error']['code'] == 'not_found'
        assert client.post('/health').status_code == 405


def test_configuration(monkeypatch, tmp_path):
    env = tmp_path / '.env'
    env.write_text('OLLAMA_CHAT_MODEL=from-file\n')
    monkeypatch.setenv('OLLAMA_CHAT_MODEL', 'from-environment')
    assert Settings(_env_file=env).ollama_chat_model == 'from-environment'
    monkeypatch.setenv('MAX_UPLOAD_BYTES', '0')
    with pytest.raises(ValidationError, match='max_upload_bytes'):
        create_app()


@pytest.mark.parametrize('values', [
    {'ollama_url': 'invalid'}, {'qdrant_url': 'ftp://localhost'},
    {'ollama_chat_model': '   '}, {'max_upload_bytes': -1},
])
def test_invalid_configuration(values):
    with pytest.raises(ValidationError):
        Settings(_env_file=None, **values)


def test_error_envelopes():
    app = create_app(Settings(_env_file=None))

    @app.get('/validation')
    def validation(count: int):
        return count

    @app.get('/expected')
    def expected():
        raise APIError(409, 'chat_busy', 'Another question is being processed.')

    @app.get('/unexpected')
    def unexpected():
        raise RuntimeError('/private/internal/path')

    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get('/validation?count=secret-value')
        assert response.status_code == 422
        assert response.json()['error']['code'] == 'validation_error'
        assert 'secret-value' not in response.text
        assert client.get('/expected').json()['error']['code'] == 'chat_busy'
        response = client.get('/unexpected')
        assert response.status_code == 500
        assert response.json()['error']['code'] == 'internal_error'
        assert '/private' not in response.text
