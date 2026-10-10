import json

import httpx
import pytest

from app.errors import APIError
from app.services.llm_service import AnswerService, NO_EVIDENCE


def evidence():
    return [{'payload': {'document_id': 'doc', 'document_name': 'policy.pdf',
                         'page_start': 4, 'page_end': 5, 'chunk_id': 8,
                         'text': 'Refunds are allowed within 30 days.'}}]


def test_answer_prompt_and_metadata():
    def handle(req):
        body = json.loads(req.content)
        assert body['stream'] is False
        assert 'only the supplied' in body['messages'][0]['content']
        prompt = json.loads(body['messages'][1]['content'])
        assert prompt['passages'][0]['text'] == evidence()[0]['payload']['text']
        return httpx.Response(200, json={'message': {'content': json.dumps({
            'answer': 'Refunds are allowed within **30 days**.', 'source_ids': [0, 0],
        })}})
    with httpx.Client(base_url='http://ollama', transport=httpx.MockTransport(handle)) as client:
        result = AnswerService(client, 'test').answer(' Refund policy? ', evidence())
    assert result['question'] == 'Refund policy?'
    assert result['answer'] == 'Refunds are allowed within **30 days**.'
    assert result['sources'] == [{key: value for key, value in evidence()[0]['payload'].items() if key != 'text'}]


@pytest.mark.parametrize('hits', [[], [{'payload': {'text': 'no metadata'}}]])
def test_no_evidence_does_not_call_model(hits):
    def handle(req):
        pytest.fail('No model call expected')
    with httpx.Client(base_url='http://ollama', transport=httpx.MockTransport(handle)) as client:
        result = AnswerService(client, 'test').answer('Question', hits)
    assert result['answer'] == NO_EVIDENCE and result['sources'] == []


@pytest.mark.parametrize('content', ['bad json', '{}', '{"answer":"x","source_ids":[99]}',
                                     '{"answer":"x","source_ids":[true]}', '{"answer":"","source_ids":[0]}'])
def test_invalid_output(content):
    with httpx.Client(base_url='http://ollama', transport=httpx.MockTransport(
        lambda req: httpx.Response(200, json={'message': {'content': content}})
    )) as client:
        with pytest.raises(APIError) as error:
            AnswerService(client, 'test').answer('Question', evidence())
        assert error.value.status_code == 503


def test_model_abstention_discards_unsupported_answer():
    with httpx.Client(base_url='http://ollama', transport=httpx.MockTransport(
        lambda req: httpx.Response(200, json={'message': {'content': '{"answer":"unsupported claim","source_ids":[]}'}})
    )) as client:
        result = AnswerService(client, 'test').answer('Question', evidence())
        assert result['answer'] == NO_EVIDENCE and result['sources'] == []
