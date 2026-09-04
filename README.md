# Local AI Learnings

A hands-on learning repository focused on understanding how local LLM applications work by building the core pieces manually before relying on higher-level frameworks.

The goal is not just to use AI libraries, but to understand the mechanisms behind:

- local LLM inference
- chat APIs
- tool calling
- agent loops
- embeddings
- cosine similarity
- RAG
- vector search
- reranking
- citations
- multi-step AI workflows

This repository will grow project by project as I learn and build more complete AI software systems.

---

## Learning Philosophy

The approach in this repository is:

1. Understand the concept
2. Build the core mechanism manually
3. Observe where it fails
4. Improve the design
5. Introduce libraries/frameworks only after understanding what they abstract away

For example, instead of starting directly with LangChain or LangGraph, I first implemented:

- raw Ollama API calls
- conversation state through message history
- manual tool-calling loops
- manual cosine similarity
- manual RAG retrieval
- FAISS-based vector search
- reranking

The intention is to understand the full flow before using higher-level abstractions.

---

# Projects

## 001 - Ollama Fundamentals

Introduction to running and interacting with local LLMs using Ollama.

Topics covered:

- running local models
- Ollama API usage
- `/api/generate`
- `/api/chat`
- system, user, assistant and tool roles
- streaming responses
- conversation history
- context windows
- local embeddings
- basic model behavior and inference concepts

Models used include:

- `qwen3:8b`
- `qwen3-embedding:8b`

---

## 002 - Manual Tool Calling Agent

A simple agent built without LangChain or LangGraph.

The goal was to understand what an agent actually is.

Basic flow:

```text
User
  ↓
LLM
  ↓
Tool call proposed
  ↓
Python controller
  ↓
Tool execution
  ↓
Tool result
  ↓
LLM
  ↓
Final response
```

Concepts explored:

- tool schemas
- tool calling
- controller loops
- multiple tools
- tool result messages
- multi-step execution
- dependent tool calls
- independent tool calls
- controller-side enforcement
- model vs controller responsibility

Example tools included:

- addition
- division
- current date

A key learning was:

> The model proposes actions, but the application/controller decides what actually gets executed.

---

## 003 - PDF RAG Reader

A PDF question-answering system built step by step to understand Retrieval-Augmented Generation.

The project started with sending the full PDF directly to the LLM and evolved into a proper retrieval pipeline.

### Evolution

```text
Full PDF in prompt
        ↓
Context-window limitations

Fixed-size chunking
        ↓
Embeddings

Manual cosine similarity
        ↓
Top-K retrieval

Context pollution
        ↓
Relative score filtering

Chunk relationships
        ↓
Graph-like semantic expansion

False-positive retrieval
        ↓
Reranking

Manual vector search
        ↓
FAISS
```

### Concepts covered

- PDF text extraction
- page-aware chunking
- chunk overlap
- chunk metadata
- embeddings
- semantic similarity
- dot product
- vector magnitude
- cosine similarity
- top-K retrieval
- relative similarity filtering
- chunk-to-chunk similarity
- semantic neighbor expansion
- reranking
- source grounding
- page/chunk citations
- retrieval errors vs generation errors
- FAISS vector indexing

### Current RAG Pipeline

```text
PDF
  ↓
Extract text
  ↓
Page-aware chunks
  ↓
Embeddings
  ↓
FAISS index
  ↓

User Question
  ↓
Question embedding
  ↓
FAISS retrieval
  ↓
Relative score filtering
  ↓
Semantic neighbor expansion
  ↓
Reranking
  ↓
Relevant context
  ↓
LLM
  ↓
Answer with citations
```

---

# Current Tech Stack

- Python
- Ollama
- Qwen3
- Qwen3 Embeddings
- PyPDF
- NumPy
- FAISS

Higher-level frameworks are intentionally avoided in the early projects.

---

# What I Am Learning

The broader goal is to become comfortable building production-oriented AI software systems.

Areas being explored include:

### LLM Application Fundamentals

- tokens
- embeddings
- context windows
- inference
- sampling
- transformers
- attention
- local model execution

### Agents

- tool calling
- agent loops
- state
- multi-step workflows
- retries
- error handling
- planning
- memory

### RAG

- chunking strategies
- embeddings
- vector retrieval
- semantic search
- reranking
- hybrid retrieval
- citations
- evaluation

### AI Backend Engineering

- FastAPI
- async inference
- background jobs
- queues
- caching
- streaming
- observability
- rate limiting
- deployment

### Local Model Infrastructure

- Ollama
- FAISS
- vector databases
- model serving
- GPU memory
- quantization
- latency vs throughput

---

# Planned Projects

The repository will continue with projects such as:

## 004 - Research Agent

A multi-tool research agent capable of:

- searching sources
- retrieving information
- comparing sources
- using tools
- producing cited answers

---

## 005 - SQL / Data Agent

An agent that can:

- inspect database schemas
- generate SQL
- validate queries
- execute read-only queries
- analyze results
- produce summaries

---

## 006 - MCP Agent

Learn how agents interact with external systems using the Model Context Protocol.

Topics:

- MCP servers
- MCP tools
- resources
- external integrations

---

## 007 - Agent Evaluation and Observability

Focus on evaluating AI systems rather than only building them.

Potential topics:

- retrieval quality
- answer correctness
- tool-call accuracy
- latency
- tracing
- regression testing
- prompt evaluation

---

## 008 - Production AI Service

Take an AI workflow and expose it as a production-style backend service.

Potential topics:

- FastAPI
- async Python
- queues
- retries
- caching
- streaming
- Docker
- monitoring

---

# Later Topics

After understanding the underlying mechanisms manually, the repository may explore:

- LangChain
- LangGraph
- LlamaIndex
- Qdrant
- pgvector
- HNSW
- IVF
- hybrid search
- dedicated reranker models
- conversational RAG
- multi-agent workflows
- LoRA / fine-tuning
- production LLM serving

The goal will be to compare these tools with the manually built implementations and understand exactly what each abstraction provides.

---

# Long-Term Goal

The long-term objective of this repository is to develop practical skills for building AI-powered software systems, with emphasis on:

- strong software engineering
- backend architecture
- reliable AI workflows
- local and hosted LLM integration
- retrieval systems
- agents
- observability
- production deployment

Rather than treating LLM applications as black boxes, the focus is on understanding each layer of the system and the trade-offs involved.

---

## Repository Structure

```text
local-ai-learnings/
│
├── 001-ollama-fundamentals/
├── 002-manual-tool-calling-agent/
├── 003-pdf-rag-reader/
├── notes/
├── README.md
└── .gitignore
```

More projects will be added as the learning progresses.
