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

This project intentionally uses conservative serial execution for dependent tool calls.

Strict dependency graphs, argument/result provenance, parallel scheduling, and workflow orchestration are deferred to a later dedicated project.

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
- planning
- tool orchestration
- dependency graphs
- result provenance
- serial and parallel tool execution
- retries
- error handling
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

## 004 - Tool Orchestration / Workflow Engine

Build a controller that can coordinate multiple tool calls reliably.

Topics:

- structured planning
- breaking tasks into smaller executable steps
- step IDs
- explicit `depends_on` relationships
- references to previous tool results
- argument/result provenance
- dependency graphs / DAGs
- serial vs parallel execution
- ready-step detection
- controller validation
- retries
- timeouts
- tool metadata
- side-effect policies
- re-planning after unexpected results

The progression is:

```text
LLM creates structured plan
        ↓
Controller validates plan
        ↓
Dependency graph determines ready steps
        ↓
Independent steps may run in parallel
        ↓
Dependent steps wait for actual tool results
        ↓
State is updated
        ↓
Re-plan when necessary
```

This project addresses a limitation discovered in `002`: prompts can guide tool usage, but they cannot guarantee ordering, provenance, or safe parallel execution.

---

## 005 - Research Agent

A multi-tool research agent capable of:

- searching sources
- retrieving information
- comparing sources
- using tools
- producing cited answers
- using the orchestration concepts learned in `004`

---

## 006 - SQL / Data Agent

An agent that can:

- inspect database schemas
- generate SQL
- validate queries
- execute read-only queries
- analyze results
- produce summaries
- maintain an auditable execution flow

---

## 007 - MCP Agent

Learn how agents interact with external systems using the Model Context Protocol.

Topics:

- MCP servers
- MCP tools
- resources
- external integrations
- permissions and tool boundaries

---

## 008 - Agent Evaluation and Observability

Focus on evaluating AI systems rather than only building them.

Potential topics:

- retrieval quality
- answer correctness
- tool-call accuracy
- plan correctness
- dependency/execution correctness
- latency
- tracing
- regression testing
- prompt evaluation
- failure analysis

---

## 009 - Production AI Service

Take an AI workflow and expose it as a production-style backend service.

Potential topics:

- FastAPI
- async Python
- background workers
- queues
- retries
- caching
- streaming
- rate limiting
- Docker
- monitoring
- cancellation
- concurrency

---

## 010 - Multi-Agent / LangGraph Workflows

After manually understanding tool calling and orchestration, explore higher-level workflow abstractions.

Potential topics:

- state machines
- multi-agent coordination
- graph-based workflows
- planner/executor patterns
- persistent state
- human-in-the-loop steps
- comparing framework behavior with the manually built orchestration engine

---

# Later Topics

After understanding the underlying mechanisms manually, the repository may explore:

- LangChain
- LlamaIndex
- Qdrant
- pgvector
- HNSW
- IVF
- hybrid search
- dedicated reranker models
- conversational RAG
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
├── 004-tool-orchestration/
├── 005-research-agent/
├── 006-sql-data-agent/
├── 007-mcp-agent/
├── 008-agent-evals-observability/
├── 009-production-ai-service/
├── 010-langgraph-workflows/
├── notes/
├── README.md
└── .gitignore
```

More projects will be added as the learning progresses.
