"""Configuration loaded when the application is created, not on module import."""
from pathlib import Path

from pydantic import Field, HttpUrl
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
