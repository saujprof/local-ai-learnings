"""Single-process JSON repositories. Use one server worker.

A shared lock per resolved file path coordinates threads and repository instances.
Blocking filesystem operations should be called from synchronous routes or a
thread pool, rather than directly on the async event loop.
"""
import json
import os
import tempfile
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock, RLock
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, model_validator
from typing import Literal


class Document(BaseModel):
    model_config = ConfigDict(extra='forbid')
    id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    path: str = Field(min_length=1)
    status: Literal['processing', 'ready', 'failed', 'deleting']
    created_at: str = Field(min_length=1)
    error: str | None = None


class Source(BaseModel):
    document_id: str
    document_name: str
    page_start: int = Field(ge=1)
    page_end: int = Field(ge=1)
    chunk_id: int | None = None

    @model_validator(mode='after')
    def ordered_pages(self):
        if self.page_end < self.page_start:
            raise ValueError('page_end must be at least page_start')
        return self


class Message(BaseModel):
    model_config = ConfigDict(extra='forbid')
    id: str = Field(min_length=1)
    role: Literal['user', 'assistant']
    content: str
    created_at: str = Field(min_length=1)
    sources: list[Source] | None = None


class StorageError(RuntimeError):
    """Existing data is unreadable or invalid; it must not be overwritten."""


_locks: dict[Path, RLock] = {}
_locks_guard = Lock()


class JsonStore:
    def __init__(self, path: Path, model: type[BaseModel]):
        self.path = path.resolve()
        self.model = model
        with _locks_guard:
            self.lock = _locks.setdefault(self.path, RLock())

    def read(self) -> list[dict]:
        # Caller holds the lock throughout read-modify-write transactions.
        try:
            text = self.path.read_text(encoding='utf-8')
        except FileNotFoundError:
            return []
        try:
            records = json.loads(text)
            if not isinstance(records, list):
                raise ValueError('Expected a list')
            validated = [self.model.model_validate(record).model_dump(exclude_none=True) for record in records]
            if len({record['id'] for record in validated}) != len(validated):
                raise ValueError('Duplicate IDs')
            return validated
        except (ValueError, TypeError) as exc:
            raise StorageError('Stored records are invalid; restore the data before retrying.') from exc

    def write(self, records: list[dict]) -> None:
        # Validate and serialize before touching the existing file.
        payload = json.dumps([
            self.model.model_validate(record).model_dump(exclude_none=True)
            for record in records
        ], ensure_ascii=False, indent=2)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=self.path.parent,
                                             prefix=f'.{self.path.name}.', delete=False) as output:
                temporary = Path(output.name)
                output.write(payload)
                output.flush()
                os.fsync(output.fileno())
            os.replace(temporary, self.path)
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)


class DocumentRepository:
    def __init__(self, data_dir: Path):
        self.store = JsonStore(data_dir / 'documents.json', Document)

    def list(self) -> list[dict]:
        with self.store.lock:
            return list(reversed(self.store.read()))

    def get(self, document_id: str) -> dict | None:
        with self.store.lock:
            return next((record for record in self.store.read() if record['id'] == document_id), None)

    def add(self, document: Document) -> dict:
        record = document.model_dump(exclude_none=True)
        with self.store.lock:
            records = self.store.read()
            if any(item['id'] == record['id'] for item in records):
                raise ValueError('Document ID already exists')
            self.store.write([*records, record])
        return deepcopy(record)

    def set_status(self, document_id: str, status: str, error: str | None = None) -> dict:
        with self.store.lock:
            records = self.store.read()
            for record in records:
                if record['id'] == document_id:
                    record['status'] = status
                    record.pop('error', None)
                    if error is not None:
                        record['error'] = error
                    validated = Document.model_validate(record).model_dump(exclude_none=True)
                    self.store.write(records)
                    return validated
            raise KeyError(document_id)

    def remove(self, document_id: str) -> None:
        # File/vector cleanup is the lifecycle service's responsibility.
        with self.store.lock:
            records = self.store.read()
            remaining = [record for record in records if record['id'] != document_id]
            if len(remaining) == len(records):
                raise KeyError(document_id)
            self.store.write(remaining)


class ChatRepository:
    def __init__(self, data_dir: Path):
        self.store = JsonStore(data_dir / 'chat_history.json', Message)

    def append_turn(self, question: str, answer: str, sources: list[Source]) -> list[dict]:
        if not question.strip() or not answer.strip():
            raise ValueError('A completed turn needs a question and answer')
        timestamp = datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
        turn = [
            Message(id=str(uuid4()), role='user', content=question.strip(), created_at=timestamp),
            Message(id=str(uuid4()), role='assistant', content=answer, created_at=timestamp, sources=sources),
        ]
        records = [message.model_dump(exclude_none=True) for message in turn]
        with self.store.lock:
            self.store.write([*self.store.read(), *records])
        return deepcopy(records)

    def page(self, limit: int = 10, offset: int = 0) -> dict:
        if not 1 <= limit <= 100 or offset < 0:
            raise ValueError('Invalid pagination')
        with self.store.lock:
            records = self.store.read()
        end = max(0, len(records) - offset)
        start = max(0, end - limit)
        return {'messages': records[start:end], 'hasMore': start > 0}
