import json

import httpx
import pytest

from app.errors import APIError
from app.services.routing_service import Route, RoutingService


def service_with(*contents, error=None):
    remaining = list(contents)

    def handle(request):
        if error is not None:
            raise error(request)
        body = json.loads(request.content)
        assert body['model'] == 'router-model'
        assert body['stream'] is False
        assert body['options']['temperature'] == 0
        if 'format' in body:
            assert 'If unsure, choose RAG' in body['messages'][0]['content']
        else:
            assert len(body['messages']) == 2
            assert body['messages'][1]['role'] == 'user'
            assert 'recent' not in json.dumps(body).lower()
        return httpx.Response(200, json={'message': {'content': remaining.pop(0)}})

    client = httpx.Client(base_url='http://ollama', transport=httpx.MockTransport(handle))
    return client, RoutingService(client, 'router-model')


@pytest.mark.parametrize(('payload', 'route'), [
    ('{"route":"GENERAL"}', Route.GENERAL),
    ('{"route":"RAG"}', Route.RAG),
])
def test_valid_routes(payload, route):
    client, router = service_with(payload)
    try:
        result = router.route('message', [{'role': 'user', 'content': 'history'}])
        assert result.route == route
    finally:
        client.close()


@pytest.mark.parametrize('payload', [
    '', 'not json', '{}', '{"route":"UNKNOWN"}',
    '{"route":"GENERAL","answer":"Hi","extra":true}',
])
def test_invalid_output_falls_back_to_rag(payload, caplog):
    client, router = service_with(payload)
    try:
        result = router.route('message')
        assert result.route == Route.RAG
        assert 'falling back to RAG' in caplog.text
    finally:
        client.close()


def test_transport_failure_falls_back_to_rag(caplog):
    client, router = service_with(error=lambda request: httpx.ReadTimeout('slow', request=request))
    try:
        assert router.route('Hi').route == Route.RAG
        assert 'falling back to RAG' in caplog.text
    finally:
        client.close()


def test_general_answer_uses_current_message_without_history():
    client, router = service_with('A short joke.')
    try:
        assert router.answer_general('Tell me a short joke') == 'A short joke.'
    finally:
        client.close()


@pytest.mark.parametrize('payload', ['', '   ', None, {}])
def test_invalid_general_answer_is_rejected(payload):
    client, router = service_with(payload)
    try:
        with pytest.raises(APIError) as exc_info:
            router.answer_general('Hi')
        assert exc_info.value.code == 'dependency_unavailable'
    finally:
        client.close()
