import json
from unittest.mock import Mock

import httpx
import pytest

from app.services.reranker_service import RerankerService
from app.services.retrieval_service import RetrievalService


def hit(index, score, document='ready'):
    return {'id': index, 'score': score, 'payload': {'document_id': document, 'text': f'Passage {index}'}}


def test_filter_rank_and_ready_documents():
    repo, embeddings, vectors, reranker = Mock(), Mock(), Mock(), Mock()
    repo.list.return_value = [{'id': 'ready', 'status': 'ready'}, {'id': 'failed', 'status': 'failed'}]
    embeddings.embed.return_value = [[1, 2]]
    vectors.search.return_value = [hit(1, .9), hit(2, .8), hit(3, .4), hit(4, 1, 'failed')]
    reranker.rerank.side_effect = lambda question, hits, limit: list(reversed(hits))[:limit]
    service = RetrievalService(repo, embeddings, vectors, reranker)
    assert [item['id'] for item in service.retrieve(' Question ')] == [2, 1]
    vectors.search.assert_called_once_with([1, 2], 10, document_ids=['ready'])
    assert [item['id'] for item in reranker.rerank.call_args.args[1]] == [1, 2]
    repo.list.return_value = []
    embeddings.reset_mock()
    assert service.retrieve('question') == []
    embeddings.embed.assert_not_called()


@pytest.mark.parametrize('content, expected', [
    ('{"ids":[1,0]}', [2, 1]), ('{"ids":[]}', []),
    ('bad json', [1, 2]), ('{"ids":[99]}', [1, 2]),
    ('{"ids":[0,0]}', [1, 2]), ('{"ids":[true]}', [1, 2]),
])
def test_reranker_contract(content, expected):
    def respond(req):
        body = json.loads(req.content)
        assert body['stream'] is False
        assert 'untrusted' in body['messages'][0]['content']
        return httpx.Response(200, json={'message': {'content': content}})
    with httpx.Client(base_url='http://ollama', transport=httpx.MockTransport(respond)) as client:
        result = RerankerService(client, 'test').rerank('question', [hit(1, .9), hit(2, .8)], 2)
        assert [item['id'] for item in result] == expected


def test_deleted_during_reranking():
    repo, embeddings, vectors, reranker = Mock(), Mock(), Mock(), Mock()
    repo.list.side_effect = [[{'id': 'ready', 'status': 'ready'}], []]
    embeddings.embed.return_value = [[1, 2]]
    vectors.search.return_value = [hit(1, .9)]
    reranker.rerank.return_value = [hit(1, .9)]
    assert RetrievalService(repo, embeddings, vectors, reranker).retrieve('question') == []


@pytest.mark.parametrize('hits', [[], [hit(1, 0)], [hit(1, -0.5)]])
def test_no_evidence_skips_reranker(hits):
    repo, embeddings, vectors, reranker = Mock(), Mock(), Mock(), Mock()
    repo.list.return_value = [{'id': 'ready', 'status': 'ready'}]
    embeddings.embed.return_value = [[1, 2]]
    vectors.search.return_value = hits
    assert RetrievalService(repo, embeddings, vectors, reranker).retrieve('question') == []
    reranker.rerank.assert_not_called()
