# 06 - Tool Policies and Reliability

This is the sixth stage of the Tool Orchestration project.

Stage 05 added parallel execution for independent ready steps. Stage 06 adds execution policies and basic reliability controls so the controller can decide not only **what is ready**, but also **how a tool is allowed to run** and **what happens when execution fails**.

## Goal

```text
Validated plan
↓
DAG scheduler
↓
READY steps
↓
inspect tool policy
├── parallel-safe → parallel executor
└── not parallel-safe → serial executor
↓
approval check
↓
execute tool
↓
success?
├── yes → DONE
└── no
    ↓
    idempotent + retries remaining?
    ├── yes → retry
    └── no → FAILED
```

The LLM still proposes the workflow. The controller owns execution policy.

## Tool Metadata

Each tool now carries metadata describing how it may be executed.

```python
"meta_data": {
    "read_only": True,
    "side_effecting": False,
    "parallel_safe": True,
    "idempotent": True,
    "requires_approval": False,
    "timeout_seconds": 5,
    "max_retries": 3,
}
```

The planner does not decide these values. They are controller-owned policy.

## Policy Meaning

`read_only` means the tool reads data without intentionally changing external state.

`side_effecting` means the tool changes external state, for example booking a hotel, sending an email, or making a payment.

`parallel_safe` controls whether a ready tool may run concurrently with other ready tools.

```text
parallel_safe = True
→ parallel executor

parallel_safe = False
→ serial executor
```

Dependency rules and parallel safety are separate. A step may depend on previous steps and still be parallel-safe once it becomes ready.

`idempotent` controls whether the controller may safely retry a failed tool automatically.

`requires_approval` adds an approval gate before execution.

## Serial and Parallel Execution

Stage 06 splits the ready batch into two groups:

```text
READY steps
↓
inspect parallel_safe
├── True  → parallel batch
└── False → serial batch
```

Both execution paths return the same result structure. The controller merges the results and updates workflow state afterward.

## Approval Gate

A tool marked:

```python
requires_approval = True
```

must pass an approval check before execution.

The current code uses:

```python
approved = True
```

as a placeholder for a future real approval mechanism such as user confirmation, a UI action, or a policy service.

The important rule is:

```text
approval happens BEFORE execution
```

## Retry Policy

Tool failures are handled inside `execute_step()`.

The controller reads:

```text
max_retries
idempotent
```

from tool metadata.

```text
tool call
↓
fails
↓
idempotent?
├── no → fail immediately
└── yes
    ↓
    retries remaining?
    ├── yes → retry
    └── no → fail permanently
```

This avoids blindly retrying tools that might create duplicate side effects.

For example:

```text
search_flights
idempotent = True
→ safe to retry

make_payment
idempotent = False
→ do not blindly retry
```

## Structured Failure Results

When a worker fails after retries are exhausted, the executor stores structured failure information:

```python
{
    "status": "FAILED",
    "error": "error message",
    "step": step
}
```

The error is stored as a string so workflow state can later be serialized, persisted, or sent back to an LLM.

## Workflow State

Success path:

```text
pending
↓
ready
↓
done
```

Failure path:

```text
pending
↓
ready
↓
tool failure
↓
retry policy
↓
failed
```

Stage 06 treats an unrecoverable step failure as terminal for the workflow.

That is intentional. Re-planning after failure belongs to Stage 07.

## Failure Ownership

The controller first handles technical reliability itself.

```text
recoverable failure
→ controller retries

unrecoverable failure
→ mark FAILED
→ stop workflow
```

The LLM is not called again for every technical failure.

## Timeout Policy

Tool metadata already contains:

```python
timeout_seconds
```

but this stage does not enforce a generic thread-level timeout.

That is intentional.

For real I/O tools, timeout handling should preferably live at the actual operation boundary, for example:

```text
HTTP request timeout
database timeout
subprocess timeout
```

A ThreadPoolExecutor timeout only stops the controller from waiting; it does not safely terminate an already-running Python thread.

## Current Architecture

```text
User request
↓
LLM planner
↓
structured plan
↓
validator
↓
DAG scheduler
↓
READY steps
↓
tool metadata
├── parallel-safe → parallel executor
└── serial-only   → serial executor
↓
approval gate
↓
tool execution
↓
retry / idempotency policy
↓
DONE or FAILED
```

## Main Learning

```text
LLM
→ decides WHAT should happen

controller
→ decides WHEN and HOW it is allowed to happen
```

Tool metadata gives the controller deterministic execution rules instead of relying on the LLM for safety and reliability decisions.

## Current Limitations

This stage intentionally does not yet include:

```text
real approval UI
generic forced thread cancellation
workflow resume after failure
failure classification
LLM re-planning
alternative tool selection
```

## Next

Stage 07 adds Re-planning.

```text
workflow fails or produces an unusable result
↓
controller builds execution context
↓
LLM receives:
- original request
- current plan
- completed results
- failed step
- failure reason
↓
LLM proposes a revised plan
↓
validator checks it
↓
controller continues
```
