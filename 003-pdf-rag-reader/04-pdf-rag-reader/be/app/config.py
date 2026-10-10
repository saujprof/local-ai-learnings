"""Configuration loaded when the application is created, not on module import."""
from pathlib import Path

from pydantic import Field, HttpUrl, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', extra='ignore')

    ollama_url: HttpUrl = HttpUrl('http://127.0.0.1:11434')
    ollama_chat_model: str = Field(default='qwen3:8b', min_length=1, pattern=r'\S')
    ollama_embedding_model: str = Field(default='qwen3-embedding:8b', min_length=1, pattern=r'\S')
    qdrant_url: HttpUrl = HttpUrl('http://127.0.0.1:6333')
    uploads_dir: Path = Path('./uploads')
    data_dir: Path = Path('./data')
    max_upload_bytes: int = Field(default=50 * 1024 * 1024, gt=0)
    qdrant_collection: str = Field(default='pdf_chunks', min_length=1, pattern=r'\S')
    dependency_timeout_seconds: float = Field(default=120, gt=0)
    embedding_batch_size: int = Field(default=16, ge=1)

    retrieval_top_k: int = Field(default=10, ge=1, le=100)
    retrieval_relative_threshold: float = Field(default=0.7, ge=0, le=1)
    retrieval_final_k: int = Field(default=4, ge=1, le=100)

    chat_context_messages: int = Field(default=10, ge=1, le=100)
    chat_context_characters: int = Field(default=6000, ge=1)

    @model_validator(mode='after')
    def validate_retrieval_limits(self):
        if self.retrieval_final_k > self.retrieval_top_k:
            raise ValueError('retrieval_final_k must not exceed retrieval_top_k')
        return self
