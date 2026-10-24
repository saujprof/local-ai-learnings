# 02 - Dependencies and Result References

This is the second stage of the Tool Orchestration project.

The planner now expresses not only **which tools should run**, but also which steps depend on other steps and which arguments should come from the actual result of an earlier step.

No tools are executed in this stage.

## Goal

```text
User request
↓
LLM planner
↓
Structured plan
↓
Execution dependencies + data references
```

Example flow:

```text
search outbound flight ──┐
search return flight ────┼──► calculate total cost
search hotel ────────────┘
```

## New Concepts

### `depends_on`

`depends_on` describes execution ordering.

```json
{
  "step_id": 3,
  "depends_on": [0, 1, 2]
}
```

This means step `3` must wait until steps `0`, `1`, and `2` finish. Independent steps use `[]`.

### `result_of`

`result_of` describes data flow.

```json
"to_flight_cost": {
  "result_of": 0
}
```

This means the argument should use the actual output produced by step `0`. The planner does not invent values that only become available after execution.

## Why Both Are Needed

```text
depends_on
→ when a step may run

result_of
→ where an argument's value comes from
```

A step may depend on another step without directly consuming its output, so the two concepts remain separate.

## Planner Rules Added in This Stage

The planner is instructed to:

- include `depends_on` for every step
- use `[]` for independent steps
- reference earlier outputs using `{"result_of": <step_id>}`
- keep `result_of` step IDs numeric
- include referenced steps in `depends_on`
- never invent outputs from earlier steps

## Example Plan

```json
[
  {
    "step_id": 0,
    "tool": "search_flights",
    "arguments": {
      "from": "Kanpur",
      "to": "Delhi",
      "date": {"day": 25, "month": 10, "year": null}
    },
    "depends_on": []
  },
  {
    "step_id": 1,
    "tool": "search_flights",
    "arguments": {
      "from": "Delhi",
      "to": "Kanpur",
      "date": {"day": 29, "month": 10, "year": null}
    },
    "depends_on": []
  },
  {
    "step_id": 2,
    "tool": "search_hotels",
    "arguments": {
      "city": "Delhi",
      "check_in": {"day": 25, "month": 10, "year": null},
      "check_out": {"day": 29, "month": 10, "year": null}
    },
    "depends_on": []
  },
  {
    "step_id": 3,
    "tool": "calculate_cost",
    "arguments": {
      "to_flight_cost": {"result_of": 0},
      "from_flight_cost": {"result_of": 1},
      "hotel_cost": {"result_of": 2}
    },
    "depends_on": [0, 1, 2]
  }
]
```

## What We Observed

Repeated runs showed that dependency structure can remain stable even when the model interprets ambiguous user details differently. For example, the hotel checkout date sometimes varied because the phrase `for 4 days and return on 29th` is ambiguous.

```text
structurally valid plan
≠
semantically correct plan
```

That becomes important in later validation and clarification handling.

## Current Scope

This version still does not validate:

```text
unknown tool names
invalid argument names
duplicate step IDs
missing dependency steps
invalid result_of references
self dependencies
dependency cycles
```

The planner is still an LLM, so its output should not be trusted automatically.

## Next

Stage 03 adds controller-side validation.

```text
LLM plan
↓
Controller validation
↓
accept or reject
```

The controller will verify that the plan is structurally valid before any execution begins.
