"""Qdrant REST operations for a single unnamed cosine-vector collection."""
from dataclasses import asdict
from urllib.parse import quote
from uuid import NAMESPACE_URL, uuid5

import httpx

from app.services.embedding_service import request, validate_vectors
from app.services.pdf_service import PDFChunk


class QdrantStore:
    def __init__(self, client: httpx.Client, collection: str):
        if not collection.strip():
            raise ValueError('Collection name is required')
        self.client = client
        self.path = '/collections/' + quote(collection, safe='')

    def ensure_collection(self, dimension: int) -> None:
        if dimension < 1:
            raise ValueError('Vector dimension must be positive')
        response = request(self.client, 'GET', self.path, allow_not_found=True)
        if response.status_code == 404:
            request(self.client, 'PUT', self.path, json={'vectors': {'size': dimension, 'distance': 'Cosine'}})
        else:
            vectors = response.json()['result']['config']['params']['vectors']
            if vectors.get('size') != dimension or vectors.get('distance') != 'Cosine':
                raise ValueError('Collection vector dimensions or distance differ; use a new collection and reindex.')

    def upsert(self, chunks: list[PDFChunk], vectors: list[list[float]]) -> None:
        validate_vectors(vectors, len(chunks))
        if not chunks:
            return
        self.ensure_collection(len(vectors[0]))
        for start in range(0, len(chunks), 64):
            points = [
                {'id': str(uuid5(NAMESPACE_URL, f'{chunk.document_id}:{chunk.chunk_id}')),
                 'vector': vector, 'payload': asdict(chunk)}
                for chunk, vector in zip(chunks[start:start + 64], vectors[start:start + 64])
            ]
            request(self.client, 'PUT', self.path + '/points', params={'wait': 'true'}, json={'points': points})

    def search(self, vector: list[float], limit: int = 10) -> list[dict]:
        validate_vectors([vector], 1)
        if not 1 <= limit <= 100:
            raise ValueError('limit must be between 1 and 100')
        self.ensure_collection(len(vector))
        response = request(self.client, 'POST', self.path + '/points/query', json={
            'query': vector, 'limit': limit, 'with_payload': True, 'with_vector': False,
        })
        return response.json()['result']['points']

    def delete_document(self, document_id: str) -> None:
        if not document_id:
            raise ValueError('Document ID is required')
        request(self.client, 'POST', self.path + '/points/delete', params={'wait': 'true'}, json={
            'filter': {'must': [{'key': 'document_id', 'match': {'value': document_id}}]},
        })
