# 03 - FAISS RAG

This version keeps the RAG flow from V2 but replaces the manual cosine-similarity scan with FAISS.

```text
PDF
↓
Page-aware chunking
↓
Chunk embeddings
↓
Normalize embeddings
↓
FAISS IndexFlatIP
↓
Persist FAISS index

Question
↓
Question embedding
↓
Normalize query
↓
FAISS search
↓
Top-K candidate chunks
↓
Relative similarity filtering
↓
LLM reranking
↓
Final Top-K chunks
↓
LLM answer + citations
```

## What This Version Covers

- FAISS vector indexing
- `IndexFlatIP`
- L2 normalization
- cosine-style similarity using normalized inner product
- exact vector search
- FAISS row position vs application chunk ID
- Top-K retrieval
- relative similarity filtering
- LLM reranking
- FAISS index persistence with `write_index()` / `read_index()`
- separation of indexing and query flows

## What FAISS Replaces

In V2, every question embedding was manually compared with every chunk embedding using Python and cosine similarity.

```text
V2

Question embedding
↓
Compare with chunk 1
Compare with chunk 2
Compare with chunk 3
...
↓
Sort results
```

In V3, FAISS performs that vector search:

```text
V3

Question embedding
↓
FAISS index.search(...)
↓
Nearest chunk vectors
```

The rest of the RAG pipeline remains mostly unchanged.

## Why `IndexFlatIP`?

`IndexFlatIP` can be read as:

```text
Index → searchable vector index
Flat  → exact search across all stored vectors
IP    → inner product
```

`Flat` means FAISS still compares the query against every stored vector. It is an exact search, not an approximate one.

Before adding vectors to the index, chunk embeddings are normalized:

```python
faiss.normalize_L2(np_embeddings)
```

The query embedding is normalized in the same way.

For normalized vectors:

```text
|A| = 1
|B| = 1
```

so cosine similarity:

```text
(A · B) / (|A| × |B|)
```

becomes:

```text
A · B
```

Therefore:

```text
normalized vectors + IndexFlatIP
≈ cosine-similarity search
```

## Indexing Flow

The PDF is processed once:

```text
PDF
↓
Create chunks
↓
Generate embeddings
↓
Store chunk text + metadata + embeddings in JSON
↓
Normalize embeddings
↓
Build FAISS index
↓
Persist index
```

The FAISS index is saved with:

```python
faiss.write_index(faiss_index, "faiss_index.index")
```

This avoids rebuilding the index every time a question is asked.

## Query Flow

For each question:

```text
Question
↓
Generate embedding
↓
Normalize embedding
↓
Load persisted FAISS index
↓
Search Top-K candidates
↓
Map FAISS rows back to chunks
↓
Relative filter
↓
Rerank
↓
Final Top-K chunks
↓
Generate grounded answer
```

The persisted index is loaded with:

```python
faiss.read_index("faiss_index.index")
```

## FAISS Row vs Chunk ID

FAISS returns positions in the vector index, not application chunk IDs.

If vectors were added in the same order as the `chunks` list:

```text
FAISS row 0 → chunks[0]
FAISS row 1 → chunks[1]
FAISS row 2 → chunks[2]
```

So the returned FAISS position can be mapped directly back to:

```python
chunk = chunks[faiss_row]
```

The chunk's own `id`, page information, and text remain application metadata.

## Retrieval Quality

FAISS changes how the vector search is executed, but it does not automatically improve semantic retrieval quality.

For example, a useful chunk may still rank lower by embedding similarity.

The current pipeline therefore still uses:

```text
FAISS retrieval
↓
relative similarity filtering
↓
LLM reranking
↓
final Top-K context
```

Reranking remains responsible for identifying which retrieved chunks are most useful for answering the exact question.

## Current Pipeline

```text
Question
↓
qwen3-embedding:8b
↓
Normalized query vector
↓
FAISS IndexFlatIP
↓
Top-K candidates
↓
Relative similarity threshold
↓
Qwen reranker
↓
Final Top-K chunks
↓
Qwen3:8b
↓
Answer with chunk/page citations
```

## Key Learning

FAISS does not replace RAG logic.

It replaces the manual vector-search step with an optimized vector index while the surrounding retrieval, filtering, reranking, context construction, and generation logic stays the same.

## Next: 04 - Scalable Vector DB RAG

V4 will move from local JSON + FAISS files to a production-shaped RAG backend using a vector database.

The goal will be a cloneable system with:

- multi-document ingestion
- persistent vector storage
- metadata filtering
- document delete / re-index
- API endpoints
- citations
- reranking
- configuration
- Docker
- tests
- a minimal UI
