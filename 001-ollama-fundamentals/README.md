# 001 - Ollama Fundamentals

This project contains the first experiments in running and interacting with a local LLM using Ollama.

The goal is to understand the basic application flow before moving into tool calling, agents, RAG, and higher-level frameworks.

---

## What This Project Covers

- starting the Ollama server
- pulling and running a local model
- making a first `/api/generate` request
- non-streaming responses
- streaming responses
- using `/api/chat`
- system, user, and assistant message roles
- maintaining conversation history
- basic system prompts

Model used:

```text
qwen3:8b
```

---

# 1. Start Ollama

Start the Ollama server:

```bash
ollama serve
```

By default, Ollama exposes its local API at:

```text
http://localhost:11434
```

To check the installed Ollama version:

```bash
ollama -v
```

---

# 2. Pull a Model

Download a model locally:

```bash
ollama pull qwen3:8b
```

You can also run it directly from the terminal:

```bash
ollama run qwen3:8b
```

To see currently loaded/running models:

```bash
ollama ps
```

---

# 3. First Generate Call

`basic.py` demonstrates the simplest API call using:

```text
POST /api/generate
```

Example request structure:

```python
data = {
    "model": "qwen3:8b",
    "prompt": "Who are you ?",
    "stream": False
}
```

The request is sent to:

```text
http://localhost:11434/api/generate
```

With:

```python
stream = False
```

Ollama waits until generation is complete and returns the response as one JSON object.

The generated text is available in:

```python
res.json()["response"]
```

---

# 4. Streaming Responses

`basic_stream.py` demonstrates streaming.

The request uses:

```python
"stream": True
```

and the HTTP request is also opened in streaming mode:

```python
requests.post(
    url=url,
    json=data,
    stream=True
)
```

The response arrives incrementally.

Each line can be processed as it arrives:

```python
for line in res.iter_lines():
    if line:
        data = json.loads(line)
        print(data["response"])
```

Conceptually:

```text
Non-streaming

Request
   ↓
Model generates full answer
   ↓
Complete response


Streaming

Request
   ↓
Model generates
   ↓
chunk
   ↓
chunk
   ↓
chunk
   ↓
done
```

Streaming does not create conversation state.

It only changes how the HTTP response is delivered.

---

# 5. Generate API vs Chat API

Ollama provides different APIs for different interaction styles.

## `/api/generate`

Useful for simple prompt-based generation.

```text
prompt
  ↓
model
  ↓
generated text
```

Example:

```python
{
    "model": "qwen3:8b",
    "prompt": "Who are you?",
    "stream": False
}
```

## `/api/chat`

Useful when the application needs structured conversation messages.

```text
messages
   ↓
model
   ↓
assistant message
```

Example message structure:

```python
messages = [
    {
        "role": "system",
        "content": "You are a personal health coach."
    },
    {
        "role": "user",
        "content": "How can I improve my sleep?"
    }
]
```

The chat API is better suited for:

- conversations
- system prompts
- message history
- tool calling
- agents

---

# 6. Message Roles

`chat.py` uses structured messages.

The main roles are:

## System

Provides high-level behavior or instructions to the model.

Example:

```python
{
    "role": "system",
    "content": "You are a personal health coach. Your name is Heal."
}
```

## User

Represents input from the user.

```python
{
    "role": "user",
    "content": "How are you?"
}
```

## Assistant

Represents a previous model response.

```python
{
    "role": "assistant",
    "content": "I am doing well."
}
```

These messages together form the conversation that is sent to the model.

---

# 7. System Prompts

A system prompt is used to define the model's behavior for the conversation.

Example:

```python
{
    "role": "system",
    "content": "You are a personal health coach. Your name is Heal."
}
```

The model then receives this instruction along with the rest of the conversation.

System prompts can be used to control things such as:

- role
- tone
- response style
- constraints
- task-specific behavior

They guide model behavior, but application code should still enforce rules that must be guaranteed.

---

# 8. Conversation History

An important learning is that the HTTP API itself is stateless.

The model does not automatically remember earlier API requests.

Conversation state is maintained by the application.

The application keeps a `messages` list:

```python
messages = [
    {
        "role": "system",
        "content": "You are a personal health coach."
    }
]
```

After the model responds:

```python
messages.append({
    "role": "assistant",
    "content": agent_message
})
```

After the user sends another message:

```python
messages.append({
    "role": "user",
    "content": user_input
})
```

The entire updated message history is then sent again with the next request.

Conceptually:

```text
Request 1

system
user
   ↓
LLM
   ↓
assistant


Request 2

system
user
assistant
user
   ↓
LLM
   ↓
assistant
```

So:

> Conversation memory exists because the application keeps and resends conversation history.

It is not automatically stored inside the model between HTTP requests.

---

---

# 9. How the LLM Handles a Request

The application-level flow is:

```text
Python application
      ↓ HTTP
Ollama server
      ↓
Local model
      ↓
Generated response
```

But inside the model, the request goes through another sequence of steps.

For example, if the application sends:

```text
What is the capital of Germany?
```

the model does not directly reason over the raw string as plain text.

A simplified model-level flow is:

```text
Text
  ↓
Tokenizer
  ↓
Token IDs
  ↓
Token embeddings
  ↓
Transformer layers
  ↓
Attention + MLP
  ↓
Final hidden representation
  ↓
Logits over the vocabulary
  ↓
Sampling / token selection
  ↓
Next token
  ↓
Repeat
```

## 9.1 Tokenization

The input text is first split into tokens.

Conceptually:

```text
"What is the capital of Germany?"
        ↓
["What", " is", " the", " capital", " of", " Germany", "?"]
```

The exact token boundaries depend on the tokenizer used by the model.

Each token is mapped to a numeric token ID:

```text
token
  ↓
token ID
```

The model operates on these token IDs rather than directly on the original characters.

## 9.2 Token Embeddings

Each token ID is mapped to an embedding vector.

Conceptually:

```text
token ID
   ↓
[0.12, -0.08, 0.43, ...]
```

The embedding is a numerical representation that the neural network can process.

So the input becomes a sequence of vectors:

```text
token 1 → vector
token 2 → vector
token 3 → vector
...
```

## 9.3 Transformer Layers

The token vectors pass through many Transformer layers.

A simplified Transformer layer can be viewed as:

```text
Attention
   ↓
Residual connection
   ↓
MLP / Feed Forward Network
   ↓
Residual connection
```

Each layer follows the same general structure, but each layer has its own learned weights.

## 9.4 Attention

Attention allows each token to use information from other relevant tokens in the available context.

For each token, the model creates:

```text
Query
Key
Value
```

vectors.

A token's Query is compared with the Keys of other tokens.

Conceptually:

```text
Query(token A)
      ↓
compare with
      ↓
Key(token B)
Key(token C)
Key(token D)
```

The resulting attention scores determine how strongly information from the corresponding Value vectors should contribute.

Modern Transformer models use multiple attention heads in parallel.

Their outputs are combined and projected back into the model representation.

## 9.5 MLP / Feed Forward Network

After attention, the representation for each token passes through a feed-forward neural network.

A simplified view is:

```text
input
  ↓
expand
  ↓
activation / gating
  ↓
shrink
  ↓
output
```

This further transforms the token representation before it moves to the next Transformer layer.

## 9.6 Final Token Prediction

After the final Transformer layer, the model produces a score for every possible token in its vocabulary.

These scores are called:

```text
logits
```

Conceptually:

```text
token A → 4.2
token B → 1.3
token C → -0.8
...
```

These logits are converted into probabilities, and the decoding strategy selects the next token.

## 9.7 Autoregressive Generation

The selected token is appended to the existing sequence.

The model then predicts the next token again.

```text
Prompt
  ↓
predict token 1
  ↓
Prompt + token 1
  ↓
predict token 2
  ↓
Prompt + token 1 + token 2
  ↓
...
```

This is why LLM text generation happens token by token.

Streaming exposes these generated pieces to the application incrementally, while non-streaming waits for the generation to finish before returning the response.

## 9.8 What Ollama Handles

The application does not manually perform tokenization, attention, Transformer execution, or token sampling.

Ollama and the underlying model runtime handle those steps.

The application mainly controls things such as:

- which model is used
- prompt or messages
- system instructions
- conversation history
- whether the response is streamed
- model/runtime options

Conceptually:

```text
Python application
      ↓
HTTP request
      ↓
Ollama
      ↓
Tokenizer
      ↓
Model inference
      ↓
Generated tokens
      ↓
HTTP response
      ↓
Python application
```

---

# 10. LLM vs Agent

An LLM and an agent are not the same thing.

The LLM works at the model level:

```text
text
→ tokens
→ embeddings
→ Transformer layers
→ logits
→ generated tokens
```

An agent is application logic built around an LLM.

Conceptually:

```text
User request
    ↓
LLM
    ↓
Model may propose an action/tool call
    ↓
Application/controller
    ↓
Tool execution
    ↓
Tool result
    ↓
LLM
    ↓
Final response
```

So the agent does not operate inside the Transformer.

The LLM generates outputs, while the surrounding application decides how those outputs are used.

This distinction becomes the focus of the next project:

```text
002 - Manual Tool Calling Agent
```


# Files

```text
001-ollama-fundamentals/
├── README.md
├── basic.py
├── basic_stream.py
└── chat.py
```

## `basic.py`

First non-streaming call using `/api/generate`.

## `basic_stream.py`

Streaming response example using `/api/generate`.

## `chat.py`

Basic conversational loop using `/api/chat`, including:

- a system prompt
- assistant messages
- user messages
- conversation history

---

# Key Learnings

### Ollama runs the model locally

The application communicates with Ollama through a local HTTP API.

```text
Python application
      ↓ HTTP
Ollama
      ↓
Local model
```

### Streaming is still HTTP

Streaming does not require WebSockets.

The server can keep an HTTP response open and send generated chunks incrementally.

### HTTP calls are stateless

Conversation state has to be maintained by the application.

### The model only sees what is included in the request

If previous messages are not sent again, the model cannot use them as conversation context.

### `/api/chat` provides a structured conversation format

This becomes important later for:

- tools
- agents
- RAG
- multi-step workflows

---

# Next Project

The next project builds on these fundamentals:

```text
002 - Manual Tool Calling Agent
```

It introduces:

- tool schemas
- function calling
- tool execution
- function registries
- tool result messages
- controller loops
- dependent and serial tool calls

The goal is to understand how an agent works before using frameworks such as LangChain or LangGraph.
