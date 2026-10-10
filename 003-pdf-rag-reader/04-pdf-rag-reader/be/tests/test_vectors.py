import httpx
import pytest

from app.errors import APIError
from app.services.embedding_service import EmbeddingService
from app.services.pdf_service import PDFChunk
from app.vector_store.qdrant_store import QdrantStore


def test_embed_batches_and_validation():
    import json
    requests = []
    def handle(req):
        body = json.loads(req.content)
        requests.append(body)
        return httpx.Response(200, json={'embeddings': [[1., 2.] for _ in body['input']]})
    with httpx.Client(base_url='http://ollama', transport=httpx.MockTransport(handle)) as client:
        service = EmbeddingService(client, 'test', 2)
        assert len(service.embed(['a', 'b', 'c'])) == 3
        assert [len(body['input']) for body in requests] == [2, 1]
        assert requests[0]['truncate'] is False
        assert service.embed([]) == []
        with pytest.raises(ValueError):
            service.embed([' '])


@pytest.mark.parametrize('vectors', [[], [[0, 0]], [[float('nan'), 1]], [[1], [1, 2]]])
def test_bad_embeddings(vectors):
    import json
    with httpx.Client(base_url='http://ollama', transport=httpx.MockTransport(
        lambda req: httpx.Response(200, content=json.dumps({'embeddings': vectors}))
    )) as client:
        with pytest.raises(APIError):
            EmbeddingService(client, 'test').embed(['text'])


def test_qdrant_lifecycle():
    import json
    calls = []
    exists = False
    def handle(req):
        nonlocal exists
        body = json.loads(req.content) if req.content else None
        calls.append((req.method, req.url.path, body))
        if req.method == 'GET':
            return httpx.Response(200, json={'result': {'config': {'params': {'vectors': {'size': 2, 'distance': 'Cosine'}}}}}) if exists else httpx.Response(404)
        exists = True
        if req.url.path.endswith('/query'):
            return httpx.Response(200, json={'result': {'points': [{'score': 0.9, 'payload': {'document_id': 'doc'}}]}})
        return httpx.Response(200, json={'result': True})
    with httpx.Client(base_url='http://qdrant', transport=httpx.MockTransport(handle)) as client:
        store = QdrantStore(client, 'chunks')
        chunk = PDFChunk('doc', 'file.pdf', 0, 1, 1, 'text')
        store.upsert([chunk], [[1, 2]])
        store.upsert([chunk], [[1, 2]])
        puts = [body for method, path, body in calls if path.endswith('/points')]
        assert puts[0] == puts[1]
        assert puts[0]['points'][0]['payload']['page_start'] == 1
        assert store.search([1, 2])[0]['score'] == 0.9
        store.delete_document('doc')
        assert calls[-1][2]['filter']['must'][0]['match']['value'] == 'doc'
        with pytest.raises(ValueError, match='dimensions'):
            store.ensure_collection(3)


def test_timeout():
    def handle(req):
        raise httpx.ReadTimeout('timeout', request=req)
    with httpx.Client(base_url='http://ollama', transport=httpx.MockTransport(handle)) as client:
        with pytest.raises(APIError) as error:
            EmbeddingService(client, 'test').embed(['text'])
        assert error.value.status_code == 504
