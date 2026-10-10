from contextlib import contextmanager
from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app
from app.storage.repositories import Document


def application(tmp_path):
    app = create_app(Settings(_env_file=None, data_dir=tmp_path, chat_context_characters=20))
    app.state.documents.add(Document(id='doc', name='file.pdf', path='unused.pdf', status='ready', created_at='now'))
    retrieval, answers = Mock(), Mock()
    retrieval.retrieve.return_value = []
    answers.answer.side_effect = lambda question, evidence, context: {'question': question, 'answer': 'No evidence.', 'sources': []}
    @contextmanager
    def retrievers(*args):
        yield retrieval
    @contextmanager
    def answer_clients(*args):
        yield answers
    app.state.chat.retrievers, app.state.chat.answers = retrievers, answer_clients
    return app, retrieval, answers


def test_chat_history_context_and_restart(tmp_path):
    app, retrieval, answers = application(tmp_path)
    with TestClient(app) as client:
        assert client.get('/chat').json() == {'messages': [], 'hasMore': False}
        assert client.post('/chat', json={'question': ' First? '}).json()['question'] == 'First?'
        assert client.post('/chat', json={'question': 'Then?'}).status_code == 200
        context = answers.answer.call_args.kwargs['context']
        assert context and sum(len(item['content']) for item in context) <= 20
        assert len(client.get('/chat').json()['messages']) == 4
        assert client.get('/chat?limit=2').json()['hasMore']
        assert len(client.get('/chat?limit=2&offset=2').json()['messages']) == 2
        ids = [item['id'] for item in client.get('/chat').json()['messages']]
    with TestClient(create_app(Settings(_env_file=None, data_dir=tmp_path))) as client:
        assert [item['id'] for item in client.get('/chat').json()['messages']] == ids


def test_failures_and_concurrency_guard(tmp_path):
    app, _, answers = application(tmp_path)
    with TestClient(app, raise_server_exceptions=False) as client:
        for question in ['', '  ', 42, None]:
            assert client.post('/chat', json={'question': question}).status_code == 422
        assert client.get('/chat?limit=0').status_code == 422
        assert client.get('/chat?offset=-1').status_code == 422
        app.state.chat.lock.acquire()
        try:
            assert client.post('/chat', json={'question': 'Question'}).json()['error']['code'] == 'chat_busy'
        finally:
            app.state.chat.lock.release()
        answers.answer.side_effect = RuntimeError('failure')
        assert client.post('/chat', json={'question': 'Question'}).status_code == 500
        assert client.get('/chat').json()['messages'] == []
        assert not app.state.chat.lock.locked()
        app.state.documents.set_status('doc', 'failed')
        assert client.post('/chat', json={'question': 'Question'}).json()['error']['code'] == 'no_ready_documents'
