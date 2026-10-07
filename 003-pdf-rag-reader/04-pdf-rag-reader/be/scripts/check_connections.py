"""Run inside the backend container: python -m scripts.check_connections."""
import json
import sys
from urllib.request import urlopen

from app.config import Settings


def main() -> int:
    settings = Settings()
    targets = {
        'Backend': 'http://127.0.0.1:8000/health',
        'Qdrant': f'{str(settings.qdrant_url).rstrip("/")}/collections',
        'Ollama': f'{str(settings.ollama_url).rstrip("/")}/api/tags',
    }
    failed = False
    for name, url in targets.items():
        try:
            with urlopen(url, timeout=5) as response:
                payload = json.load(response)
            print(f'{name}: reachable')
            if name == 'Ollama':
                available = {model['name'] for model in payload.get('models', [])}
                for model in (settings.ollama_chat_model, settings.ollama_embedding_model):
                    if model not in available:
                        print(f'  Missing configured model: {model}')
                        failed = True
        except Exception as exc:
            print(f'{name}: failed ({exc})')
            failed = True
    return int(failed)


if __name__ == '__main__':
    sys.exit(main())
