# 01 - Full Document Prompting

This is the simplest version of the PDF QA system.

The complete PDF text is extracted and sent to the LLM together with the user's question.

```text
PDF
↓
Extract all text
↓
Add document to chat context
↓
Ask question
↓
LLM answer
```

No chunking, embeddings, vector search, or RAG is used yet.

---

## What This Version Covers

- PDF text extraction with `pypdf`
- sending the full document to Ollama
- keeping document context separate from the changing user question
- grounding answers in the provided document
- understanding context-window limitations

---

## Why Keep Document and Question Separate?

The document usually stays the same while questions change.

```text
Document → mostly fixed
Question → changes
```

The application therefore keeps the PDF as context and adds each question separately.

However, Ollama does not permanently remember the document. Every API request still needs the relevant message history to be sent again.

---

## Current Flow

```text
PDF
↓
PyPDF
↓
Full extracted text
↓
messages
├── system instructions
├── document context
└── user question
↓
Ollama /api/chat
↓
Qwen3:8b
↓
Answer
```

The system prompt tells the model to answer only from the document and to say when information is not available.

---

## Testing

A fictional PDF is used so that answers are unlikely to come from the model's pretrained knowledge.

Example questions:

- Who was the pilot manager?
- Which block saved the most water?
- Why was the Maple alert on 3 July false?
- What was the final project spend?
- What is ORBIT-18?

A useful grounding test is to ask something not present in the PDF, for example:

```text
What was Mira Sen's previous job?
```

The model should respond that the information is not available in the document.

---

## Limitation

This approach works for small documents, but it does not scale.

```text
Larger PDF
↓
More prompt tokens
↓
Higher latency and context usage
↓
Context-window limit
```

It is also inefficient to send an entire large document when only a small section may be relevant to the question.

This limitation leads to the next version.

---

## Next: 02 - Manual RAG

```text
PDF
↓
Chunking
↓
Embeddings
↓
Manual cosine similarity
↓
Top-K relevant chunks
↓
LLM
```

Instead of sending the complete PDF, V2 will retrieve and send only the most relevant parts of the document.
