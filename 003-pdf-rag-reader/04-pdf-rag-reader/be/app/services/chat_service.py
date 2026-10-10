"""Synchronous, single-conversation orchestration."""
from threading import Lock

from app.errors import APIError
from app.services.vector_clients import answer_client, retrieval_client
from app.storage.repositories import Source


class ChatService:
    def __init__(self, settings, documents, history, retrievers=retrieval_client, answers=answer_client):
        self.settings, self.documents, self.history = settings, documents, history
        self.retrievers, self.answers = retrievers, answers
        self.lock = Lock()

    def ask(self, question: str) -> dict:
        if not self.lock.acquire(blocking=False):
            raise APIError(409, 'chat_busy', 'Another question is being processed.')
        try:
            if not any(record['status'] == 'ready' for record in self.documents.list()):
                raise APIError(409, 'no_ready_documents', 'Upload a PDF and wait until it is ready.')
            recent = self.history.page(limit=self.settings.chat_context_messages)['messages']
            # Bound the total text sent as conversation context, newest first.
            remaining = self.settings.chat_context_characters
            context = []
            for message in reversed(recent):
                content = message['content'][-remaining:]
                context.append({'role': message['role'], 'content': content})
                remaining -= len(content)
                if remaining <= 0:
                    break
            context.reverse()
            with self.retrievers(self.settings, self.documents) as retrieval:
                evidence = retrieval.retrieve(question, context=context)
            with self.answers(self.settings) as answers:
                result = answers.answer(question, evidence, context=context)
            self.history.append_turn(result['question'], result['answer'],
                                     [Source.model_validate(source) for source in result['sources']])
            return result
        finally:
            self.lock.release()
