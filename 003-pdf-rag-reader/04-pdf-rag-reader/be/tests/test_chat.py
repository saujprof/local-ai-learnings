from contextlib import contextmanager
from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app
from app.services.routing_service import Route, RouteResult
from app.storage.repositories import Document


def application(tmp_path):
    app = create_app(Settings(_env_file=None, data_dir=tmp_path, chat_context_characters=20))
    app.state.documents.add(Document(id='doc', name='file.pdf', path='unused.pdf', status='ready', created_at='now'))
    router, retrieval, answers = Mock(), Mock(), Mock()
    router.route.return_value = RouteResult(route=Route.RAG)
    router.answer_general.return_value = 'General answer.'
    retrieval.retrieve.return_value = []
    answers.answer.side_effect = lambda question, evidence, context: {'question': question, 'answer': 'No evidence.', 'sources': []}
    @contextmanager
    def retrievers(*args):
        yield retrieval
    @contextmanager
    def answer_clients(*args):
        yield answers
    @contextmanager
    def routers(*args):
        yield router
    app.state.chat.routers = routers
    app.state.chat.retrievers, app.state.chat.answers = retrievers, answer_clients
    return app, router, retrieval, answers


def test_chat_history_context_and_restart(tmp_path):
    app, router, retrieval, answers = application(tmp_path)
    with TestClient(app) as client:
        assert client.get('/chat').json() == {'messages': [], 'hasMore': False}
        assert client.post('/chat', json={'question': ' First? '}).json()['question'] == 'First?'
        assert client.post('/chat', json={'question': 'Then?'}).status_code == 200
        context = answers.answer.call_args.kwargs['context']
        assert context and sum(len(item['content']) for item in context) <= 20
        router_context = router.route.call_args.args[1]
        assert router_context == []
        assert len(client.get('/chat').json()['messages']) == 4
        assert client.get('/chat?limit=2').json()['hasMore']
        assert len(client.get('/chat?limit=2&offset=2').json()['messages']) == 2
        ids = [item['id'] for item in client.get('/chat').json()['messages']]
    with TestClient(create_app(Settings(_env_file=None, data_dir=tmp_path))) as client:
        assert [item['id'] for item in client.get('/chat').json()['messages']] == ids


def test_failures_and_concurrency_guard(tmp_path):
    app, _, _, answers = application(tmp_path)
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


def test_general_route_needs_no_document_and_skips_rag(tmp_path):
    app = create_app(Settings(_env_file=None, data_dir=tmp_path))
    router, retrieval, answers = Mock(), Mock(), Mock()
    router.route.return_value = RouteResult(route=Route.GENERAL)
    router.answer_general.return_value = 'Hi! How can I help?'

    @contextmanager
    def routers(*args):
        yield router

    @contextmanager
    def should_not_run(*args):
        pytest.fail('RAG dependencies must not run for GENERAL messages')
        yield

    app.state.chat.routers = routers
    app.state.chat.retrievers = should_not_run
    app.state.chat.answers = should_not_run

    with TestClient(app) as client:
        response = client.post('/chat', json={'question': 'Hi'})
        assert response.status_code == 200
        assert response.json() == {
            'question': 'Hi', 'answer': 'Hi! How can I help?', 'sources': [],
        }
        router.answer_general.assert_called_once_with('Hi')
        messages = client.get('/chat').json()['messages']
        assert [message['content'] for message in messages] == ['Hi', 'Hi! How can I help?']
        assert messages[1]['sources'] == []


def test_router_receives_recent_history_for_ambiguous_followup(tmp_path):
    app = create_app(Settings(
        _env_file=None,
        data_dir=tmp_path,
        router_context_messages=2,
        router_context_characters=100,
    ))
    router = Mock()
    router.route.side_effect = [
        RouteResult(route=Route.GENERAL),
        RouteResult(route=Route.RAG),
    ]
    router.answer_general.return_value = 'Happy to help.'

    @contextmanager
    def routers(*args):
        yield router

    app.state.chat.routers = routers
    with TestClient(app) as client:
        assert client.post('/chat', json={'question': 'Thanks'}).status_code == 200
        response = client.post('/chat', json={'question': 'Tell me more about that'})
        assert response.status_code == 409
        assert response.json()['error']['code'] == 'no_ready_documents'

    followup_context = router.route.call_args_list[1].args[1]
    assert followup_context == [
        {'role': 'user', 'content': 'Thanks'},
        {'role': 'assistant', 'content': 'Happy to help.'},
    ]
