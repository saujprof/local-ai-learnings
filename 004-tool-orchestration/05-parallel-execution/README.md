# 05 - Parallel Execution

This is the fifth stage of the Tool Orchestration project.

The previous stage could execute a validated dependency graph, but ready steps were still executed one by one.

This stage adds concurrent execution for independent ready steps.

## Goal

```text
Validated plan
↓
Find READY steps
↓
Run independent READY steps concurrently
↓
Collect results
↓
Update workflow state
↓
Unlock dependent steps
```

For the current travel workflow:

```text
          ┌── step_0: outbound flight ──┐
start ────┼── step_1: return flight ────┼──► step_3: calculate_cost
          └── step_2: hotel search ─────┘
```

Steps `0`, `1`, and `2` are independent and can run at the same time.

Step `3` still waits until all three are complete.

## What Changed from 04

Stage 04 already had:

```text
planner
validator
dependency tracking
ready-step detection
tool execution
result storage
result_of resolution
```

The only major change here is how a batch of ready steps is executed.

Before:

```text
step_0
↓
step_1
↓
step_2
```

Now:

```text
step_0 ─┐
step_1 ─┼── run concurrently
step_2 ─┘
```

## ThreadPoolExecutor

Parallel execution uses:

```python
from concurrent.futures import ThreadPoolExecutor, as_completed
```

This is a good fit for I/O-bound tool work such as HTTP calls, database calls, file operations, and remote services.

The executor uses:

```python
ThreadPoolExecutor(max_workers=4)
```

## Parallel Batch Execution

The controller first gathers all steps currently marked `ready`.

Each ready step is submitted to the thread pool with:

```python
executor.submit(execute_step, ...)
```

`as_completed(...)` is then used to collect results as individual futures finish.

Conceptually:

```text
ready steps
↓
submit all futures
↓
workers run tools
↓
future completes
↓
collect result
```

## Shared State Ownership

Worker threads do not directly update:

```python
steps_status
steps_results
```

Instead:

```text
worker
→ execute tool
→ return result

controller
→ collect result
→ store result
→ mark step done
```

This keeps workflow state changes centralized.

## Runtime Result Flow

Example runtime values:

```text
step_0 → 5000
step_1 → 5000
step_2 → 9000
```

After the parallel batch completes:

```python
steps_results = {
    "step_0": 5000,
    "step_1": 5000,
    "step_2": 9000
}
```

Then the next DAG iteration sees that step `3` has all dependencies complete.

Its references:

```json
{
  "to_flight_cost": {"result_of": 0},
  "from_flight_cost": {"result_of": 1},
  "hotel_cost": {"result_of": 2}
}
```

resolve to the actual runtime values before `calculate_cost` executes.

## Important Learning

Parallel scheduling does not change dependency rules.

```text
DAG scheduler
→ decides which steps may run

parallel executor
→ runs those independent ready steps concurrently
```

The controller still owns workflow state and dependency decisions.

## Timing Intuition

If independent tools take:

```text
step_0 → 3 seconds
step_1 → 3 seconds
step_2 → 2 seconds
```

Sequential execution is roughly:

```text
3 + 3 + 2 = 8 seconds
```

Parallel execution is roughly:

```text
max(3, 3, 2) = 3 seconds
```

plus small scheduling overhead.

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
DAG Scheduler
↓
READY batch
↓
ThreadPoolExecutor
├── worker: step_0
├── worker: step_1
└── worker: step_2
↓
Controller collects results
↓
Update state
↓
Next DAG iteration
```

## Current Limitations

This stage still assumes every ready tool is safe to run in parallel.

It does not yet handle:

```text
parallel_safe policies
side-effecting tools
retries
timeouts
FAILED state
RUNNING state
idempotency
approval requirements
re-planning
```

## Next

Stage 06 adds Tool Policies and Reliability.

The next questions become:

```text
What if a tool fails?
What if it hangs?
Should it retry?
Is it safe to run in parallel?
Does it create side effects?
Does it require approval?
```
