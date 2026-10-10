"""Retrieve evidence only; answer generation is a separate unit."""
import math


class RetrievalService:
    def __init__(self, repository, embeddings, vectors, reranker, top_k=10, relative_threshold=0.7, final_k=4):
        if not 1 <= final_k <= top_k <= 100 or not 0 <= relative_threshold <= 1:
            raise ValueError('Invalid retrieval configuration')
        self.repository, self.embeddings, self.vectors, self.reranker = repository, embeddings, vectors, reranker
        self.top_k, self.relative_threshold, self.final_k = top_k, relative_threshold, final_k

    def retrieve(self, question: str, context: list[dict] | None = None) -> list[dict]:
        question = question.strip()
        if not question:
            raise ValueError('Question must not be blank')
        ready = {record['id'] for record in self.repository.list() if record['status'] == 'ready'}
        if not ready:
            return []
        search_question = question
        if context:
            recent_questions = [item['content'] for item in context if item['role'] == 'user']
            if recent_questions:
                search_question = 'Previous questions: ' + '\n'.join(recent_questions) + '\nCurrent question: ' + question
        vector = self.embeddings.embed([search_question])[0]
        hits = self.vectors.search(vector, self.top_k, document_ids=sorted(ready))
        candidates = []
        seen = set()
        for hit in hits:
            payload = hit.get('payload', {})
            score = hit.get('score')
            identity = hit.get('id')
            if (not isinstance(payload, dict) or payload.get('document_id') not in ready or
                    not isinstance(payload.get('text'), str) or not payload['text'].strip() or
                    type(score) not in (int, float) or not math.isfinite(score) or score <= 0):
                continue
            if identity is not None and identity in seen:
                continue
            seen.add(identity)
            candidates.append(hit)
        candidates.sort(key=lambda hit: hit['score'], reverse=True)
        if not candidates:
            return []
        cutoff = candidates[0]['score'] * self.relative_threshold
        candidates = [hit for hit in candidates if hit['score'] >= cutoff][:self.top_k]
        ranked = self.reranker.rerank(search_question, candidates, self.final_k)
        # A deletion may have started while the model was reranking.
        ready_now = {record['id'] for record in self.repository.list() if record['status'] == 'ready'}
        return [hit for hit in ranked if hit['payload']['document_id'] in ready_now]
