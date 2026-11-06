# 07 — Re-planning

A failed workflow should not simply call the original planner again.
Re-planning needs execution state, failure context, attempt history, validation, and bounded retries.

```text
initial planner
      ↓
   validator
      ↓
   executor
      ↓
deterministic failure analysis
      ↓
controller builds normalized replan context
      ↓
classifier: RE_PLAN / REPLY_BACK
      ↓ RE_PLAN
context + attempt history
      ↓
dedicated replanner
      ↓
validate_plan()
      ↓
validate_revision()
      ↓
semantic reviewer
   valid ↓       ↓ invalid
 executor    feedback → replanner
```

## Main idea

The LLM proposes how the workflow should change, but the controller owns workflow state and decides whether a candidate plan is safe to execute.

The controller is responsible for:

- keeping replan state local to one workflow run,
- recording failed attempts,
- limiting the number of replans,
- rejecting repeated failed searches,
- preserving plan structure and result provenance,
- separating execution failures from semantic rejections,
- and executing a revised plan only after deterministic and semantic checks pass.

The model is used only where reasoning is useful:

- deciding `RE_PLAN` vs `REPLY_BACK`,
- generating a revised plan,
- reviewing whether the revised plan still preserves user intent and is internally coherent.

## Flow

### 1. Initial planning

`planner.py` converts the user's request into a structured tool plan.

The planner does not execute tools.

Example:

```json
[
  {
    "step_id": 0,
    "tool": "search_flights",
    "arguments": {
      "from": "Kanpur",
      "to": "Delhi",
      "date": {"day": 25, "month": 11, "year": 2026}
    },
    "depends_on": []
  },
  {
    "step_id": 1,
    "tool": "search_hotels",
    "arguments": {
      "city": "Delhi",
      "check_in": {"day": 25, "month": 11, "year": 2026},
      "check_out": {"day": 29, "month": 11, "year": 2026}
    },
    "depends_on": []
  },
  {
    "step_id": 2,
    "tool": "search_flights",
    "arguments": {
      "from": "Delhi",
      "to": "Kanpur",
      "date": {"day": 29, "month": 11, "year": 2026}
    },
    "depends_on": []
  },
  {
    "step_id": 3,
    "tool": "calculate_cost",
    "arguments": {
      "to_flight_cost": {"result_of": 0},
      "from_flight_cost": {"result_of": 2},
      "hotel_cost": {"result_of": 1}
    },
    "depends_on": [0, 1, 2]
  }
]
```

## 2. Current-date context

The planner should not guess missing years from model knowledge.

`get_current_date()` reads the current date in `Asia/Kolkata` before planning and passes that context to the model.

If the user omits the travel year, the current year is used consistently for flight and hotel dates. An explicitly supplied year always takes priority.

Other missing values remain `null` unless they can be derived unambiguously.

## 3. Execution and failure detection

The existing DAG executor is reused.

Independent ready steps can execute in parallel, while tools marked `parallel_safe=False` execute serially.

Tool policy metadata still controls:

- `parallel_safe`
- `idempotent`
- `requires_approval`
- `max_retries`
- timeout metadata

The executor records local runtime state:

```text
steps_status
steps_results
plan
```

`analyse_result()` is deterministic. It only detects whether a step failed.

It does not decide how to recover.

## 4. Normalized replan context

Raw executor state is converted into a smaller, explicit context before asking a model to reason about recovery.

`build_replan_context()` records:

```text
original_request
current_date
current_plan
successful_steps
failed_step
failed_result
all failures
pending_steps
decision_reason
attempt_history
```

This avoids making the model reconstruct workflow state from a large raw dump.

Attempt history is especially important.

Example:

```text
attempt 1: hotel 25–29 → NO_RESULT
attempt 2: hotel 26–30 → NO_RESULT
```

The replanner can see older failures and should not repeat them.

## 5. Replan classifier

The classifier chooses exactly one next action:

```text
RE_PLAN
REPLY_BACK
```

It does not generate a plan.

`NO_RESULT` is treated differently from a technical failure:

```text
NO_RESULT
→ tool executed successfully
→ no matching result was found
→ replanning may help if the user allowed relevant flexibility
```

Example:

```text
"around 25th"
→ date is explicitly flexible
→ RE_PLAN may be allowed
```

while:

```text
"on 25th"
→ strict date
→ changing it would require user permission
→ REPLY_BACK
```

The classifier uses temperature `0` because this stage should behave like a decision function rather than a creative generation step.

## 6. Dedicated replanner

`re_plan_trip()` is separate from the initial planner.

It receives the normalized context and generates a complete revised plan.

The replanner should:

- preserve the original objective,
- preserve strict constraints,
- change only explicitly flexible constraints,
- preserve required actions,
- preserve step IDs, tool names, dependencies, and `result_of` references,
- keep related values internally consistent,
- avoid previous failed search arguments,
- make the smallest reasonable change,
- and never infer the cause of `NO_RESULT` unless the tool explicitly reports one.

Replanning is therefore not:

```text
failure → ask the initial planner again
```

It is:

```text
failure
+
execution state
+
attempt history
+
allowed flexibility
→ revised plan
```

## 7. Revision validation

Every revised plan first passes the normal plan validator.

`validate_revision()` then applies replan-specific guards.

It preserves:

- required actions,
- tool ordering,
- dependency edges,
- parallelism,
- `result_of` provenance,
- and previously failed argument history.

A candidate that repeats a previously failed search is rejected before execution.

## 8. Semantic reviewer

A structurally valid plan may still be semantically poor.

Examples:

```text
outbound flight: 25 Nov
hotel check-in: 24 Nov
```

or:

```text
user requested Delhi
replanner changes destination to another city
```

A narrow semantic reviewer checks only:

- whether the revised plan preserves the user's intent,
- whether strict constraints are preserved,
- whether flexible constraints are changed reasonably,
- whether related dates and duration remain coherent.

It returns only:

```json
{"valid": true, "reason": ""}
```

or:

```json
{
  "valid": false,
  "reason": "specific actionable feedback"
}
```

The reviewer does not replan or execute tools.

If the reviewer rejects the candidate, its feedback is added to context and sent back to the replanner.

History distinguishes:

```text
execution_failure
semantic_rejection
```

A semantic rejection is not treated as an executed tool failure.

## 9. Bounded replanning

`controller.run_workflow()` owns the replan budget.

The default is two replans.

This prevents loops such as:

```text
plan A → NO_RESULT
plan B → NO_RESULT
plan A → NO_RESULT
plan B → NO_RESULT
...
```

If the workflow cannot produce a valid alternative within the limit, it returns control to the user.

## Model

The current implementation uses:

```text
gpt-oss:20b
```

through the local Ollama server.

Earlier versions used `qwen3:8b`. The larger model showed better behavior on replanning because it more reliably preserved related constraints across multiple tools.

The controller and validators are still required even with a stronger model. Model quality improves reasoning, but does not replace deterministic workflow guarantees.

## Current limitations

Successful steps are included in replan context, but a revised plan currently executes in full. Successful-result reuse is intentionally deferred.

The example tools are mocked. `search_hotels()` currently always returns `NO_RESULT` so bounded replanning can be observed reliably.

Semantic review is still performed by an LLM, so it can be too strict or too permissive. Future versions can make user constraints more explicit, for example:

```json
{
  "departure_date": {
    "target": "2026-11-25",
    "flexible": true,
    "tolerance_days": 1
  }
}
```

That is an optimization/refinement, not required for the core replanning architecture demonstrated here.

## Files

```text
planner.py
    initial structured planner

controller.py
    owns workflow execution, history, replan limits and revision flow

executor.py
    DAG execution, concurrency and tool-policy handling

replanner.py
    failure analysis, context building, classifier, replanner and semantic reviewer

validator.py
    structural, argument, dependency and result-reference validation

tools.py
    tool definitions, metadata and current-date helper
```

## Run

Start Ollama with `gpt-oss:20b` available, then run:

```sh
python planner.py
```

The hotel stub intentionally returns `NO_RESULT`, so the run demonstrates the failure → classify → replan → review → bounded retry path.

## What this stage teaches

The main lesson from 07 is:

```text
replanning is not "ask the LLM again"
```

A reliable replanning loop needs:

```text
execution state
+
normalized failure context
+
attempt history
+
constraint preservation
+
deterministic validation
+
semantic review
+
bounded retries
```

With that architecture in place, 07 is complete and the next step is to integrate the full workflow into **08 — Final Travel Workflow Agent**.
