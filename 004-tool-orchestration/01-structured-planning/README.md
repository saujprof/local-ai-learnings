# 01 - Structured Planning

This is the first stage of the Tool Orchestration project.

The goal is to convert a natural-language travel request into a structured, machine-readable plan of tool calls.

No tools are executed in this stage.

## Goal

```text
User request
↓
LLM planner
↓
Structured JSON plan
```

Example request:

```text
I want to travel from Kanpur to Delhi on 25th of October for 4 days and return on 29th.
```

Expected plan shape:

```json
[
  {
    "step_id": 0,
    "tool": "search_flights",
    "arguments": {
      "from": "Kanpur",
      "to": "Delhi",
      "date": {
        "day": 25,
        "month": 10,
        "year": null
      }
    }
  }
]
```

## Available Tools

This version uses three mock tool definitions:

```text
search_flights
search_hotels
calculate_cost
```

The tools are only described to the planner.

They are not executed through Ollama's tool-calling interface.

## Why We Do Not Use Ollama `tools`

Passing tools through Ollama's `tools` field tells the model to perform tool calling.

That is different from planning.

```text
Tool calling
→ model proposes an immediate tool call

Structured planning
→ model returns a future workflow plan
```

The available tools are therefore included as normal prompt context.

## Planner Rules

The planner is instructed to:

- return JSON only
- give every step a unique sequential ID
- use only available tools
- use exact tool and parameter names
- include every explicitly requested action when a tool supports it
- use only tools necessary for the request
- avoid inventing missing information
- prefer explicit user values over inferred values
- derive values only when unambiguous
- use `null` for unknown required values
- never execute tools

## Important Learning

Getting valid JSON is not enough.

A useful workflow plan must also be:

```text
complete
faithful to the user request
machine-readable
based only on available tools
free from invented values
```

During this stage, several planner failure modes became visible:

```text
tool calling instead of planning
invented dates / years
unstable output schemas
missing requested actions
unnecessary tool usage
invented placeholder values
```

The structured planner prompt reduces these problems by defining an explicit output contract.

## Current Flow

```text
User request
↓
Planner prompt
↓
Available tool descriptions
↓
qwen3:8b
↓
JSON plan
```

## Current Scope

This version does not yet handle:

```text
depends_on
result references
tool execution
plan validation
dependency graphs
parallel execution
retries
timeouts
re-planning
```

Those are introduced in later stages.

## Next

The next stage adds:

```text
explicit dependencies
+
references to previous tool results
```

Example:

```text
search flights ──┐
                  ├── calculate cost
search hotels ───┘
```

This is where the planner starts expressing how later steps depend on actual outputs from earlier steps.
