from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch

import pytest

from app.storage.repositories import ChatRepository, Document, DocumentRepository, StorageError


def document(index):
    return Document(id=str(index), name=f'{index}.pdf', path=f'uploads/{index}.pdf',
                    status='processing', created_at='2026-10-08T00:00:00Z')


def test_documents_restart_and_lifecycle(tmp_path):
    repo = DocumentRepository(tmp_path)
    assert repo.list() == []
    repo.add(document(1))
    repo.add(document(2))
    repo.set_status('1', 'failed', 'No text')
    repo = DocumentRepository(tmp_path)
    assert [item['id'] for item in repo.list()] == ['2', '1']
    assert repo.get('1')['error'] == 'No text'
    repo.set_status('1', 'ready')
    assert 'error' not in repo.get('1')
    with pytest.raises(ValueError):
        repo.add(document(1))
    repo.remove('1')
    assert repo.get('1') is None


def test_concurrent_instances(tmp_path):
    def add(index):
        DocumentRepository(tmp_path).add(document(index))
        ChatRepository(tmp_path).append_turn(f'Question {index}', f'Answer {index}', [])
    with ThreadPoolExecutor(max_workers=8) as pool:
        list(pool.map(add, range(30)))
    assert len(DocumentRepository(tmp_path).list()) == 30
    messages = ChatRepository(tmp_path).page(100)['messages']
    assert len(messages) == 60
    assert len({message['id'] for message in messages}) == 60
    for user, assistant in zip(messages[::2], messages[1::2]):
        assert user['content'].split()[-1] == assistant['content'].split()[-1]


def test_history_pagination_restart(tmp_path):
    repo = ChatRepository(tmp_path)
    assert repo.page() == {'messages': [], 'hasMore': False}
    saved = []
    for index in range(12):
        saved.extend(repo.append_turn(str(index), 'Answer', []))
    repo = ChatRepository(tmp_path)
    assert repo.page()['messages'] == saved[14:]
    assert repo.page(offset=10)['messages'] == saved[4:14]
    assert repo.page(offset=20) == {'messages': saved[:4], 'hasMore': False}
    assert repo.page(offset=100) == {'messages': [], 'hasMore': False}
    with pytest.raises(ValueError):
        repo.page(0)


def test_failed_replace_preserves_completed_turn(tmp_path):
    repo = ChatRepository(tmp_path)
    repo.append_turn('Question', 'Answer', [])
    original = repo.store.path.read_bytes()
    with patch('app.storage.repositories.os.replace', side_effect=OSError('disk failure')):
        with pytest.raises(OSError):
            repo.append_turn('Next', 'Next answer', [])
    assert repo.store.path.read_bytes() == original
    assert list(tmp_path.iterdir()) == [repo.store.path]


@pytest.mark.parametrize('contents', ['broken', '{}', '[{"id":"bad"}]'])
def test_corruption_is_not_overwritten(tmp_path, contents):
    path = tmp_path / 'documents.json'
    path.write_text(contents)
    with pytest.raises(StorageError):
        DocumentRepository(tmp_path).add(document(1))
    assert path.read_text() == contents
