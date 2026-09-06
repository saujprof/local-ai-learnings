# 002 - Manual Tool Calling Agent

This project builds a simple tool-calling agent manually using Ollama and Python.

The goal is to understand what an agent actually is before using higher-level frameworks such as LangChain or LangGraph.

The project starts with a single tool call and then evolves into a controller loop that can execute multiple tools in sequence.

---

## What This Project Covers

- defining tools for an LLM
- tool schemas
- function registries
- reading tool calls returned by the model
- executing Python functions
- sending tool results back to the model
- multiple tools
- agent/controller loops
- dependent tool calls
- serial execution
- independent vs dependent actions
- model responsibility vs controller responsibility

---

# 1. LLM vs Agent

An LLM by itself generates output.

An agent is an application built around an LLM that allows the model to request actions.

Conceptually:

```text
User
  ↓
LLM
  ↓
Tool call proposed
  ↓
Application / Controller
  ↓
Tool executed
  ↓
Tool result
  ↓
LLM
  ↓
Final response
```

The important distinction is:

> The model proposes an action. The controller decides whether and how that action is executed.

The LLM does not directly execute Python functions.

---

# 2. Why Tool Calling Is Needed

An LLM can generate text, but some tasks are better handled by external tools.

Examples:

- addition
- division
- current date
- database queries
- web search
- file lookup
- API calls

Instead of asking the model to calculate or guess everything itself, the application can expose tools that the model is allowed to request.

---

# 3. A Tool Is a Normal Python Function

A tool can start as an ordinary Python function.

Example:

```python
def add(input_1: float, input_2: float):
    return input_1 + input_2
```

The function itself does not know anything about the LLM.

It is simply application code.

The LLM needs a description of the function so it knows:

- the tool name
- what the tool does
- what arguments it expects

That description is provided through a tool schema.

---

# 4. Tool Schema

A tool schema describes a function to the model.

Conceptually:

```text
Python function
      ↓
tool schema
      ↓
LLM understands:
- tool name
- purpose
- arguments
```

Example:

```python
tools = [
    {
        "type": "function",
        "function": {
            "name": "add",
            "description": "Adds two numbers",
            "parameters": {
                "type": "object",
                "properties": {
                    "input_1": {"type": "number"},
                    "input_2": {"type": "number"}
                },
                "required": ["input_1", "input_2"]
            }
        }
    }
]
```

The schema does not execute anything.

It only tells the model which actions are available.

---

# 5. Sending Tools to the Chat API

Tool calling uses the structured chat API.

Conceptually:

```python
payload = {
    "model": "qwen3:8b",
    "messages": messages,
    "tools": tools,
    "stream": False
}
```

The model receives:

```text
conversation messages
+
available tools
```

It can then answer directly or return a structured tool call.

---

# 6. What the Model Returns

If the model decides to use a tool, the assistant response can contain a structured tool call.

Conceptually:

```text
tool name:
add

arguments:
input_1 = 150
input_2 = 39
```

The application extracts the function name and arguments from the response.

At this point nothing has been executed yet.

The model has only proposed:

```text
Call this tool with these arguments.
```

---

# 7. Function Registry

The application needs a mapping between names returned by the model and actual Python functions.

Example:

```python
function_registry = {
    "add": add
}
```

Then:

```text
"add"
  ↓
function registry
  ↓
actual Python add function
```

The controller can then execute the function with the arguments proposed by the model.

This is the point where the tool actually runs.

---

# 8. First Tool-Calling Flow

The simplest version is:

```text
User request
    ↓
LLM receives tool schema
    ↓
LLM returns tool call
    ↓
Application reads tool name + arguments
    ↓
Function registry finds Python function
    ↓
Application executes function
    ↓
Tool result
```

This demonstrates the core tool-calling mechanism.

It is not yet a full agent loop.

---

# 9. Why the Tool Result Goes Back to the LLM

If the tool returns a result such as:

```text
189
```

the model needs that result if it is expected to continue reasoning or produce a final natural-language answer.

The application therefore adds a tool-result message to conversation history.

Conceptually:

```python
{
    "role": "tool",
    "content": "189"
}
```

The conversation now contains:

```text
user request
assistant tool call
tool result
```

The model can then be called again.

---

# 10. Tool Results Are Context

The tool output is not magically stored in the model.

The controller explicitly adds it to the messages sent on the next request.

This follows the same principle from `001`:

> The application maintains state by keeping and resending conversation history.

---

# 11. Multiple Tools

Once the single-tool mechanism works, multiple tools can be exposed.

Example:

```text
add
divide
get_current_date
```

Each tool has:

```text
Python function
+
tool schema
+
function registry entry
```

The model chooses which available tool is appropriate for the current step.

---

# 12. From Tool Calling to an Agent Loop

A useful tool-using agent requires repeated interaction between the model and the application.

Conceptually:

```text
Ask model
   ↓
Did model request a tool?
   │
   ├── Yes
   │    ↓
   │  execute tool
   │    ↓
   │  append result
   │    ↓
   │  call model again
   │
   └── No
        ↓
      final answer
        ↓
      stop
```

This repeated loop is the core of a simple manual agent.

---

# 13. Serial / Dependent Tool Calls

Some tasks require one tool result before another tool can be called.

Example:

```text
I have 5 oranges from one friend and 15 from another.
How many do I have?
Then divide them among 4 children.
```

Correct sequence:

```text
add(5, 15)
      ↓
20
      ↓
divide(20, 4)
      ↓
5
```

The second tool depends on the result of the first.

Therefore the calls must happen in sequence.

---

# 14. Independent vs Dependent Tool Calls

Not every tool call needs to wait for another.

Independent example:

```text
What is today's date and what is 10 + 20?
```

These calls do not depend on each other.

Dependent example:

```text
Add 5 and 15, then divide the result by 4.
```

The division cannot happen correctly until the addition result exists.

A controller should distinguish between these cases.

---

# 15. Prompt Guidance vs Controller Enforcement

A system prompt can guide the model to issue dependent tool calls one at a time.

For example:

```text
If a tool call depends on another tool result,
request only the prerequisite tool first.
```

This can improve behavior.

But prompts are not guarantees.

The controller still decides what is actually executed.

Important principle:

```text
Prompt
  ↓
guides behavior

Controller
  ↓
enforces behavior
```


## What We Observed in Practice

While testing sequential tool use, the model correctly understood dependencies but still sometimes proposed multiple dependent calls in the same response.

Example:

```text
add(3, 6)
add(9, 3)
```

even though `9` had not yet been returned by the tool.

The model had internally calculated the intermediate result and used it to construct the next tool call.

This taught an important lesson:

> Understanding a dependency does not mean the model will always follow the desired execution protocol.

Prompt wording improved behavior in some runs, but did not guarantee it.

Therefore, rules that must be guaranteed should be enforced by application logic rather than natural-language instructions alone.

---

# 16. Conservative Controller Policy

For this learning agent, the controller intentionally executes only one tool call per iteration.

If the model returns:

```text
add(3, 6)
add(9, 3)
```

the controller accepts only:

```text
add(3, 6)
```

After the actual result `9` is returned, the updated conversation is sent back to the model so it can decide the next step.

Conceptually:

```text
LLM proposes multiple calls
        ↓
Controller accepts first call only
        ↓
Execute actual tool
        ↓
Append actual result
        ↓
Call LLM again
        ↓
Model decides next step
```

This deliberately sacrifices parallelism in exchange for simpler and safer serial execution.

---

# 17. Limitation: Serial Execution Does Not Guarantee Tool-Grounded Reasoning

Another behavior appeared with:

```text
3 + 6 + 3
then divide by 4
```

The controller executed:

```text
add(3, 6)
```

and returned:

```text
9
```

On the next iteration, the model sometimes internally calculated:

```text
9 + 3 = 12
```

and directly requested:

```text
divide(12, 4)
```

So the current controller guarantees:

```text
at most one tool execution per iteration
```

but it does not guarantee:

```text
every intermediate value must come from an actual tool result
```

---

# 18. Limitation: Missing Provenance

With a normal tool call such as:

```text
divide(12, 4)
```

the controller cannot reliably know where `12` came from.

It may have come from:

```text
- the original user input
- a previous tool result
- an internal model calculation
- a model assumption
```

The current tool-call structure gives the controller a tool name and arguments, but not explicit provenance for every argument.

Because of that, strict enforcement of tool-derived intermediate values is not possible with this protocol alone.

---

# 19. Stronger Future Protocol

Strict orchestration requires a richer protocol.

Instead of:

```text
divide(12, 4)
```

a future controller could require explicit references:

```text
call_1:
    add(3, 6)

call_2:
    add(result_of_call_1, 3)

call_3:
    divide(result_of_call_2, 4)
```

This creates an explicit dependency chain:

```text
call_1
   ↓
call_2
   ↓
call_3
```

The controller could then verify that a referenced result actually exists before executing a dependent call.

This provides provenance and stronger execution guarantees.

---

# 20. Parallelism Is a Separate Problem

Executing one tool per iteration prevents unsafe dependency assumptions, but independent calls also become serial.

For example:

```text
get_current_date()
get_weather()
```

might be safe to execute in parallel.

The current controller intentionally does not try to infer this.

A future orchestration layer may use metadata such as:

```text
read_only
side_effecting
parallel_safe
idempotent
depends_on
```

to decide which actions can run concurrently.

For this project:

> Correct, understandable serial execution is preferred over premature parallelism.

---

# 21. Current Scope of This Project

This project intentionally stops before full tool orchestration.

It covers:

```text
single tool
↓
multiple available tools
↓
manual controller loop
↓
tool-result messages
↓
serial execution
↓
basic dependency awareness
```

It does not yet implement:

```text
explicit dependency graphs
result references
strict provenance validation
parallel scheduling
retry policies
timeouts
side-effect policies
workflow DAG execution
```

Those belong to a later orchestration-focused project.

---

# 22. Model Responsibility vs Controller Responsibility

## Model

The model can:

- interpret the user request
- decide whether a tool may help
- select a tool
- generate tool arguments
- continue after receiving tool results
- generate a final response

## Controller

The application/controller must:

- define allowed tools
- validate tool names
- validate arguments
- decide whether a call is permitted
- execute actual functions
- handle errors
- append tool results
- continue or stop the loop
- enforce dependency/order rules

A useful mental model is:

```text
LLM = decision/proposal engine

Controller = execution authority
```

---

# 23. Assistant and Tool Messages

When a tool is used, conversation history should preserve what actually happened.

Conceptually:

```text
User message
    ↓
Assistant tool call
    ↓
Tool result
    ↓
Assistant next action or final response
```

A useful rule is:

> Only actions represented by actual tool-result messages should be considered executed.

---

# 24. Full Manual Agent Flow

```text
USER
  │
  ▼
MESSAGES
  │
  ▼
OLLAMA /api/chat
  │
  ▼
LLM
  │
  ├──────────── no tool call ────────────┐
  │                                       │
  ▼                                       ▼
TOOL CALL                            FINAL RESPONSE
  │
  ▼
CONTROLLER
  │
  ├─ validate tool
  ├─ validate arguments
  ├─ check dependency/order
  │
  ▼
FUNCTION REGISTRY
  │
  ▼
PYTHON TOOL
  │
  ▼
TOOL RESULT
  │
  ▼
APPEND TO MESSAGES
  │
  └────────────────────► call LLM again
```

---

# 25. Project Progression

## Stage 1 - Single Tool

Learn:

```text
tool schema
↓
tool call
↓
function registry
↓
Python execution
```

## Stage 2 - Manual Agent Loop

Learn:

```text
multiple tools
↓
tool messages
↓
controller loop
↓
dependent calls
↓
serial execution
↓
final response
```

---

# Files

Suggested structure:

```text
002-manual-tool-calling-agent/
├── README.md
├── 01_basic_tool.py
└── 02_agent_loop.py
```

### `01_basic_tool.py`

Demonstrates:

- one Python tool
- one tool schema
- tool call extraction
- function registry
- function execution

### `02_agent_loop.py`

Demonstrates:

- multiple tools
- conversation history
- assistant tool-call messages
- tool-result messages
- controller loop
- dependent tool calls
- serial execution

---

# Key Learnings

### Tool calling does not mean the LLM executes code

The model only generates a structured request. The application executes the real function.

### Tools are application capabilities exposed to the model

The controller decides which capabilities exist.

### The function registry connects model output to application code

```text
tool name
   ↓
registry
   ↓
Python function
```

### Tool results must be returned to the model

The controller adds them to conversation history before continuing.

### An agent is more than one tool call

A basic tool-using agent emerges when the application repeatedly performs:

```text
LLM
→ action
→ tool
→ observation
→ LLM
```

until the model produces a final answer.

### Dependent actions require ordering

If Tool B requires Tool A's result:

```text
Tool A
↓
result
↓
Tool B
```

The controller should enforce the order.

### The model proposes; the controller executes

This is the central principle of this project.


### One-tool-per-iteration is a controller policy

The current agent intentionally executes only the first proposed tool call on each iteration. This gives simple serial execution but sacrifices parallelism.

### Prompt instructions are not guarantees

The model may understand a dependency and still emit dependent calls together or calculate intermediate values itself.

### Current tool calls do not preserve argument provenance

The controller cannot always tell whether a value came from the user, an actual tool result, or the model's own reasoning.

### Full orchestration is intentionally deferred

Strict dependencies, result references, parallel execution, retries, timeouts, and DAG scheduling will be explored in a later orchestration-focused project.

---

# Next Project

The next project builds on model context and retrieval:

```text
003 - PDF RAG Reader
```

It explores:

- document extraction
- chunking
- embeddings
- semantic retrieval
- reranking
- vector search
- citations
- FAISS
- grounded generation
