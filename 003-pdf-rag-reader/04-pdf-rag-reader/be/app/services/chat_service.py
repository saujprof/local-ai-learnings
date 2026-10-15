"""Synchronous, single-conversation orchestration."""
import logging
import re
from threading import Lock

from app.errors import APIError
from app.services.routing_service import Route
from app.services.vector_clients import answer_client, retrieval_client, routing_client
from app.storage.repositories import Source

logger = logging.getLogger('uvicorn.error')
FOLLOW_UP_REFERENCE = re.compile(
    r'\b(it|this|that|these|those|they|them|he|she|there|former|latter|previous|above)\b'
    r'|\b(tell me more|what about|how about)\b',
    re.IGNORECASE,
)


class ChatService:
    def __init__(
        self, settings, documents, history,
        routers=routing_client, retrievers=retrieval_client, answers=answer_client,
    ):
        self.settings, self.documents, self.history = settings, documents, history
        self.routers, self.retrievers, self.answers = routers, retrievers, answers
        self.lock = Lock()

    def _context(self, message_limit: int, character_limit: int) -> list[dict]:
        recent = self.history.page(limit=message_limit)['messages']
        remaining = character_limit
        context = []
        for message in reversed(recent):
            content = message['content'][-remaining:]
            context.append({'role': message['role'], 'content': content})
            remaining -= len(content)
            if remaining <= 0:
                break
        context.reverse()
        return context

    def _router_context(self, question: str) -> list[dict]:
        if not FOLLOW_UP_REFERENCE.search(question):
            return []
        return self._context(
            self.settings.router_context_messages,
            self.settings.router_context_characters,
        )

    def ask(self, question: str) -> dict:
        if not self.lock.acquire(blocking=False):
            raise APIError(409, 'chat_busy', 'Another question is being processed.')
        try:
            logger.debug('Chat question received: %r', question)
            router_context = self._router_context(question)
            with self.routers(self.settings) as router:
                route = router.route(question, router_context)
            logger.debug('Chat route selected: %s', route.route.value)

            if route.route == Route.GENERAL:
                with self.routers(self.settings) as router:
                    answer = router.answer_general(question)
                result = {'question': question, 'answer': answer, 'sources': []}
                self.history.append_turn(question, answer, [])
                return result

            if not any(record['status'] == 'ready' for record in self.documents.list()):
                raise APIError(409, 'no_ready_documents', 'Upload a PDF and wait until it is ready.')
            context = self._context(
                self.settings.chat_context_messages,
                self.settings.chat_context_characters,
            )
            with self.retrievers(self.settings, self.documents) as retrieval:
                evidence = retrieval.retrieve(question, context=context)
            with self.answers(self.settings) as answers:
                result = answers.answer(question, evidence, context=context)
            self.history.append_turn(result['question'], result['answer'],
                                     [Source.model_validate(source) for source in result['sources']])
            return result
        finally:
            self.lock.release()
