# 02 - Manual RAG

This version builds the core RAG pipeline manually before using FAISS or a vector database.

```text
PDF
↓
Page-aware chunking
↓
Chunk embeddings
↓
Question embedding
↓
Manual cosine similarity
↓
Top-K candidates
↓
Relative similarity filtering
↓
LLM reranking
↓
Top reranked chunks
↓
LLM answer + citations
```

## What This Version Covers

- page-aware PDF chunking
- chunk overlap
- chunk metadata
- embeddings with `qwen3-embedding:8b`
- manual cosine similarity
- Top-K candidate retrieval
- relative similarity filtering
- LLM-based reranking
- grounded answer generation
- chunk/page citations

## Retrieval

Each PDF chunk is stored with its text, page information, and embedding.

For a question, the same embedding model generates a question vector. The question vector is manually compared with every chunk vector using cosine similarity.

The chunks are sorted by similarity and the Top-K candidates are selected.

A relative threshold is then applied:

```text
chunk similarity > 60% of the best candidate similarity
```

This is a relative threshold, not an absolute cosine score of `0.60`.

## Reranking

Cosine similarity finds broadly related chunks, but the highest similarity score does not always identify the chunk that best answers the question.

The selected candidates are sent to the LLM again and ranked by how relevant and useful they are for answering the exact question.

Only the top reranked chunks above the relevance threshold are used for final answer generation.

## Example Learning

For:

```text
What is ORBIT-18?
```

the chunk containing the strongest ORBIT-18 details was not among the highest cosine-ranked chunks.

Reranking moved that useful chunk into the final context, allowing the answer to include the actual ORBIT-18 details.

This shows the difference between:

```text
Embedding retrieval
→ finds broadly relevant candidates

Reranking
→ identifies which candidates best answer the question
```

## Next: 03 - FAISS RAG

V3 will keep the same RAG flow but replace the manual scan across all chunk embeddings with FAISS.

```text
V2:
question vector
→ manual cosine comparison against every chunk

V3:
question vector
→ FAISS index search
```
