# 04 - DAG Execution

This is the fourth stage of the Tool Orchestration project.

The previous stages created and validated a structured workflow plan. This stage adds actual execution.

The key idea is:

```text
LLM plans
↓
Controller validates
↓
Code executes
```

The LLM is not involved in the execution loop. Once a valid plan exists, normal Python code decides which steps are ready, executes tools, stores results, and unlocks dependent steps.

## Goal

```text
User request
↓
LLM planner
↓
Structured plan
↓
Validator
↓
Validated workflow
↓
DAG executor
↓
Tool results
```

For a travel workflow:

```text
search outbound flight ──┐
search return flight ────┼──► calculate total cost
search hotel ────────────┘
```

The first three steps are independent.

The final `calculate_cost` step can only execute after all required search steps finish.

## Project Structure

```text
04-dag-execution/
├── planner.py
├── tools.py
├── validator.py
├── executor.py
└── README.md
```

## Planner

The planner still produces the workflow definition.

Example step:

```json
{
  "step_id": 0,
  "tool": "search_flights",
  "arguments": {
    "from": "Kanpur",
    "to": "Delhi"
  },
  "depends_on": []
}
```

Dependent steps may reference earlier outputs:

```json
{
  "step_id": 3,
  "tool": "calculate_cost",
  "arguments": {
    "to_flight_cost": {
      "result_of": 0
    }
  },
  "depends_on": [0]
}
```

The planner only describes the workflow.

It does not execute tools.

## Validation Before Execution

The generated plan is parsed and passed through the controller validator before execution.

The validator checks:

```text
plan structure
step IDs
tool names
tool arguments
dependencies
result_of references
```

Only a valid plan is passed to the executor.

The runtime flow is therefore:

```text
LLM output
↓
json.loads(...)
↓
validate_plan(...)
↓
execute_plan(...)
```

## Executor State

The executor keeps runtime state for every step.

Two dictionaries are used:

```python
steps_status = {}
steps_results = {}
```

Example:

```python
steps_status = {
    "step_0": "pending",
    "step_1": "pending",
    "step_2": "pending",
    "step_3": "pending"
}
```

and:

```python
steps_results = {
    "step_0": None,
    "step_1": None,
    "step_2": None,
    "step_3": None
}
```

The status/result stores belong to a single execution run, so state does not leak between workflows.

## Step States

This stage currently uses:

```text
pending
ready
done
```

A step starts as:

```text
pending
```

When all its dependencies are complete:

```text
pending → ready
```

After successful tool execution:

```text
ready → done
```

For example:

```text
Initial

step_0 → pending
step_1 → pending
step_2 → pending
step_3 → pending
```

Since steps `0`, `1`, and `2` have no dependencies:

```text
step_0 → ready
step_1 → ready
step_2 → ready
step_3 → pending
```

After they finish:

```text
step_0 → done
step_1 → done
step_2 → done
step_3 → ready
```

Then the final step executes.

## Ready-Step Detection

A pending step becomes ready only when all steps listed in `depends_on` are complete.

Conceptually:

```text
for each pending step
    check dependencies

    if every dependency is done
        mark step ready
```

Example:

```json
{
  "step_id": 3,
  "depends_on": [0, 1, 2]
}
```

Step `3` cannot become ready until:

```text
step_0 == done
step_1 == done
step_2 == done
```

## Sequential Execution

Multiple steps may be ready at the same time.

For example:

```text
step_0
step_1
step_2
```

are independent.

In this stage they are still executed sequentially:

```text
step_0
↓
step_1
↓
step_2
```

The executor understands that they are independent, but parallel execution is intentionally deferred to the next stage.

## Tool Registry

The executor maps tool names from the plan to actual Python functions.

Example:

```python
function_map = {
    "search_flights": search_flights,
    "search_hotels": search_hotels,
    "calculate_cost": calculate_cost,
}
```

The planner produces:

```json
"tool": "search_flights"
```

The executor resolves that string to:

```python
search_flights(...)
```

This keeps planning separate from implementation.

## Mock Tools

This stage uses simple local tool implementations.

Example behavior:

```text
search_flights → returns 5000
search_hotels → returns 9000
calculate_cost → adds the values
```

The goal is to learn orchestration, not external travel APIs.

A typical execution produces:

```text
step_0 → 5000
step_1 → 5000
step_2 → 9000
step_3 → 19000
```

## Result Storage

After a tool completes, its actual output is stored:

```python
steps_results["step_0"] = 5000
```

That result becomes available to later dependent steps.

This is important because the planner does not know runtime values.

The planner only creates:

```json
{
  "result_of": 0
}
```

The controller later resolves that reference to the real result.

## Resolving `result_of`

Suppose the plan contains:

```json
{
  "to_flight_cost": {
    "result_of": 0
  },
  "from_flight_cost": {
    "result_of": 1
  },
  "hotel_cost": {
    "result_of": 2
  }
}
```

and runtime state contains:

```python
steps_results = {
    "step_0": 5000,
    "step_1": 5000,
    "step_2": 9000
}
```

The executor resolves the runtime arguments to:

```python
{
    "to_flight_cost": 5000,
    "from_flight_cost": 5000,
    "hotel_cost": 9000
}
```

Then it executes:

```python
calculate_cost(...)
```

This is where data provenance becomes concrete:

```text
planner reference
{"result_of": 0}

↓ controller resolves

actual runtime value
5000
```

## Preserving the Original Plan

Runtime argument resolution uses a copied arguments dictionary.

Conceptually:

```python
tool_args = deepcopy(step["arguments"])
```

This prevents execution from modifying the original workflow plan.

That keeps a clean distinction between:

```text
plan
→ immutable workflow description

runtime arguments
→ resolved values used during execution
```

## Full Execution Loop

The executor repeatedly performs:

```text
check whether all steps are done
↓
find pending steps whose dependencies are complete
↓
mark those steps ready
↓
execute ready steps
↓
store actual results
↓
mark completed steps done
↓
repeat
```

In simplified form:

```text
while workflow not complete:

    detect ready steps

    execute ready steps

    store results
```

## Current Architecture

```text
User
↓
LLM Planner
↓
Structured Plan
↓
Validator
↓
Validated Plan
↓
Executor
├── state tracking
├── ready-step detection
├── tool lookup
├── tool execution
├── result storage
└── result_of resolution
↓
Completed Workflow
```

## Important Learning

The main lesson from this stage is the separation between planning and execution.

```text
LLM
→ decides what should happen

Controller code
→ decides when it can happen

Tool implementation
→ performs the actual work
```

The LLM does not need to participate in every execution iteration.

That makes execution more deterministic and easier to validate.

Another important distinction becomes concrete here:

```text
depends_on
→ controls execution order

result_of
→ controls data flow
```

## Current Limitations

This stage still does not handle:

```text
parallel execution
RUNNING / FAILED states
tool failures
retries
timeouts
approval policies
side-effect protection
re-planning
```

Ready steps are executed sequentially even when they are independent.

The execution loop also assumes a validated plan and successful tool calls.

Those reliability concerns are introduced in later stages.

## Next

Stage 05 adds parallel execution.

The current executor may detect:

```text
READY:
step_0
step_1
step_2
```

but runs them sequentially.

The next stage will allow independent ready steps to run concurrently:

```text
          ┌── step_0 ──┐
start ────┼── step_1 ──┼──► step_3
          └── step_2 ──┘
```

This introduces the next orchestration question:

```text
Which ready steps are safe to execute in parallel?
```
