"""Configured clients scoped to one ingestion/query operation."""
from contextlib import contextmanager

import httpx

from app.config import Settings
from app.services.embedding_service import EmbeddingService
from app.vector_store.qdrant_store import QdrantStore


@contextmanager
def vector_clients(settings: Settings):
    with (
        httpx.Client(base_url=str(settings.ollama_url), timeout=settings.dependency_timeout_seconds) as ollama,
        httpx.Client(base_url=str(settings.qdrant_url), timeout=settings.dependency_timeout_seconds) as qdrant,
    ):
        yield (
            EmbeddingService(ollama, settings.ollama_embedding_model, settings.embedding_batch_size),
            QdrantStore(qdrant, settings.qdrant_collection),
        )


@contextmanager
def retrieval_client(settings: Settings, repository):
    from app.services.reranker_service import RerankerService
    from app.services.retrieval_service import RetrievalService

    with vector_clients(settings) as (embeddings, vectors):
        yield RetrievalService(
            repository, embeddings, vectors,
            RerankerService(embeddings.client, settings.ollama_chat_model),
            settings.retrieval_top_k, settings.retrieval_relative_threshold, settings.retrieval_final_k,
        )


@contextmanager
def answer_client(settings: Settings):
    from app.services.llm_service import AnswerService

    with httpx.Client(base_url=str(settings.ollama_url), timeout=settings.dependency_timeout_seconds) as client:
        yield AnswerService(client, settings.ollama_chat_model)
