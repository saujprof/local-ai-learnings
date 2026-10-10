"""Synchronous Ollama client; invoke from a worker thread in async workflows."""
import math
import httpx

from app.errors import APIError


def request(client: httpx.Client, method: str, path: str, allow_not_found: bool = False, **kwargs) -> httpx.Response:
    try:
        response = client.request(method, path, **kwargs)
        if not (allow_not_found and response.status_code == 404):
            response.raise_for_status()
        return response
    except httpx.TimeoutException as exc:
        raise APIError(504, 'dependency_timeout', 'A model or vector service timed out.') from exc
    except httpx.HTTPError as exc:
        raise APIError(503, 'dependency_unavailable', 'A model or vector service is unavailable or rejected the request.') from exc


def validate_vectors(vectors, count: int) -> list[list[float]]:
    if not isinstance(vectors, list) or len(vectors) != count:
        raise ValueError('Embedding count does not match inputs')
    dimension = None
    for vector in vectors:
        if not isinstance(vector, list) or not vector:
            raise ValueError('Embedding vectors must be nonempty lists')
        if dimension is None:
            dimension = len(vector)
        if len(vector) != dimension or any(
            isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value)
            for value in vector
        ):
            raise ValueError('Embedding vectors must have consistent dimensions and finite values')
        if not any(vector):
            raise ValueError('Embedding vectors must not be zero vectors')
    return vectors


class EmbeddingService:
    def __init__(self, client: httpx.Client, model: str, batch_size: int = 16):
        if batch_size < 1:
            raise ValueError('batch_size must be positive')
        self.client, self.model, self.batch_size = client, model, batch_size

    def embed(self, texts: list[str]) -> list[list[float]]:
        if any(not text.strip() for text in texts):
            raise ValueError('Embedding inputs must not be blank')
        vectors = []
        for start in range(0, len(texts), self.batch_size):
            batch = texts[start:start + self.batch_size]
            response = request(self.client, 'POST', '/api/embed', json={
                'model': self.model, 'input': batch, 'truncate': False,
            })
            try:
                vectors.extend(validate_vectors(response.json()['embeddings'], len(batch)))
            except (ValueError, KeyError, TypeError) as exc:
                raise APIError(503, 'dependency_unavailable', 'Embedding service returned invalid vectors.') from exc
        try:
            return validate_vectors(vectors, len(texts))
        except ValueError as exc:
            raise APIError(503, 'dependency_unavailable', 'Embedding dimensions changed between batches.') from exc
