from copy import deepcopy
from concurrent.futures import ThreadPoolExecutor, as_completed

from tools import get_tool_key

# Mock tool implementations keep this stage focused on orchestration.
# `search_flights` is intentionally configured to fail below so retry and
# failure-handling behavior can be tested.
search_flights_c = 0


def search_flights(**kwargs):
    global search_flights_c
    from_place = kwargs["from"]
    to_place = kwargs["to"]
    date_of_travel = kwargs["date"]

    # if search_flights_c < 2:
    #     search_flights_c += 1
    #     raise Exception("Error occured")
    raise Exception("Error occured")

    return 5000


def search_hotels(**kwargs):
    check_in = kwargs["check_in"]
    check_out = kwargs["check_out"]
    city = kwargs["city"]

    return 9000


def calculate_cost(**kwargs):
    to_flight_cost = kwargs["to_flight_cost"]
    from_flight_cost = kwargs["from_flight_cost"]
    hotel_cost = kwargs["hotel_cost"]

    cost = to_flight_cost + from_flight_cost + hotel_cost

    return cost


def check_all_steps_done(steps_status):
    """Return True only when every workflow step has completed."""
    all_done = all(status == "done" for status in steps_status.values())
    return all_done


def execute_step(step, function_map, steps_results):
    """
    Execute one workflow step.

    The original plan is kept unchanged. Runtime `result_of` references are
    resolved in a copied arguments dictionary before the tool is called.
    """
    tool = step["tool"]

    # Copy arguments so resolving runtime values does not mutate the plan.
    tool_args = deepcopy(step["arguments"])

    # Resolve references to results produced by earlier completed steps.
    # Example: {"result_of": 0} -> steps_results["step_0"]
    for arg, value in tool_args.items():
        if isinstance(value, dict) and "result_of" in value:
            result_of_step = f"step_{value['result_of']}"
            tool_args[arg] = steps_results[result_of_step]

    # Map the planned tool name to its Python implementation and execution policy.
    func = function_map[tool]
    tool_data = get_tool_key(tool)
    metadata = tool_data["function"]["meta_data"]

    # Approval is checked before a protected tool executes.
    # `approved = True` is a placeholder for a real approval mechanism.
    if metadata["requires_approval"]:
        approved = True
        if not approved:
            raise Exception("Approval not given")

    retry_count = 0
    while retry_count <= metadata["max_retries"]:
        if retry_count > 0:
            print(f"RETRYING {tool} {retry_count}")
        try:
            result = func(**tool_args)
            return result
        except Exception:
            # Only idempotent tools are retried automatically.
            if not metadata["idempotent"]:
                raise Exception("Step failed")
            retry_count += 1
    raise Exception("Step failed")


def execute_steps_in_parallel(steps_data):
    """
    Execute the current batch of ready steps concurrently.

    Worker threads execute tools and return results. Shared workflow state is
    updated later by the controller, not directly by the worker threads.
    """
    results = {}

    with ThreadPoolExecutor(max_workers=4) as executor:
        tasks = {
            executor.submit(execute_step, **step_dict): step_dict
            for step_dict in steps_data
        }

        for task in as_completed(tasks):
            t = tasks[task]
            step = t.get("step")

            try:
                t_res = task.result()
                t_name = f"step_{step["step_id"]}"
                results[t_name] = t_res
            except Exception as e:
                t_name = f"step_{step["step_id"]}"
                results[t_name] = {"status": "FAILED", "error": str(e), "step": step}

    return results

def execute_steps_in_series(steps_data):
    """
    Execute ready steps that are not marked parallel-safe one at a time.

    Results use the same structure as the parallel executor so the controller
    can handle both execution paths uniformly.
    """
    results = {}
    for step_data in steps_data:
        step = step_data.get("step")
        t_name = f"step_{step["step_id"]}"
        try:
            res = execute_step(**step_data)
            results[t_name] = res
        except Exception as e:
            results[t_name] = {"status": "FAILED", "error": str(e), "step": step}

    return results



def execute_steps(steps_status, function_map, steps_results, plan):
    """
    Execute the current ready batch according to each tool's policy.

    Parallel-safe steps go to the thread pool. Other ready steps run serially.
    The controller then merges both result sets and updates workflow state.
    """

    steps_to_execute = []
    steps_to_execute_serial = []
    for step_name, status in steps_status.items():
        if status == "ready":
            print(f"Execute {step_name}")

            # Convert "step_2" back to numeric step_id 2 and find the
            # corresponding step definition in the validated plan.
            step_id = int(step_name[5:])
            step = [s for s in plan if s["step_id"] == step_id][0]
            tool_data = get_tool_key(step["tool"])

            # Route each ready step according to its concurrency policy.
            if tool_data["function"]["meta_data"]["parallel_safe"]:
                steps_to_execute.append(
                    {
                        "step": step,
                        "function_map": function_map,
                        "steps_results": steps_results,
                    }
                )
            else:
                steps_to_execute_serial.append(
                    {
                        "step": step,
                        "function_map": function_map,
                        "steps_results": steps_results,
                    }
                )

    # Execute non-parallel-safe tools serially.
    results = execute_steps_in_series(steps_to_execute_serial)
    print("serial_results")
    print(results)

    # Execute parallel-safe tools concurrently.
    parallel_results = execute_steps_in_parallel(steps_to_execute)
    print("parallel_results")
    print(parallel_results)

    # Merge both execution paths before updating workflow state.
    results = {**results, **parallel_results}

    # Update shared workflow state only after worker execution completes.
    for step_name, result in results.items():
        if (
            result
            and isinstance(result, dict)
            and "status" in result
            and result["status"] == "FAILED"
        ):
            steps_results[step_name] = result
            steps_status[step_name] = "failed"
        else:
            steps_results[step_name] = result
            steps_status[step_name] = "done"
    print(steps_results)
    print(steps_status)


def check_dependencies_done(step, steps_status):
    """Check whether all dependencies for a step have completed."""
    for dependency in step["depends_on"]:
        step_name = f"step_{dependency}"

        if steps_status[step_name] != "done":
            return False

    return True


def check_any_dependency_failed(step, steps_status):
    """Return True if any dependency for this step has failed."""
    for dependency in step["depends_on"]:
        step_name = f"step_{dependency}"

        if steps_status[step_name] == "failed":
            return True

    return False


def execute(plan, steps_status, function_map, steps_results):
    """
    Repeatedly discover ready steps, execute them in parallel batches,
    and continue until the workflow is complete.
    """
    while not check_all_steps_done(steps_status):
        for step in plan:
            step_name = f'step_{step["step_id"]}'
            # Stage 06 treats an unrecoverable step failure as terminal.
            # Re-planning after failure is introduced in Stage 07.
            if steps_status[step_name] == "failed":
                raise Exception("Failed")
            if steps_status[step_name] == "done":
                continue
            if (
                steps_status[step_name] == "pending"
                and check_dependencies_done(step, steps_status)
                and not check_any_dependency_failed(step, steps_status)
            ):
                steps_status[step_name] = "ready"
        execute_steps(steps_status, function_map, steps_results, plan)

    print(steps_status)

    return True


def execute_plan(plan):
    """
    Initialize runtime state and execute an already validated plan.

    Status and result stores are local to a single run so workflow state
    cannot leak between executions.
    """
    steps_status = {}
    steps_results = {}

    # Tool registry used by the executor.
    function_map = {
        "search_flights": search_flights,
        "search_hotels": search_hotels,
        "calculate_cost": calculate_cost,
    }

    try:
        # Initialize execution state for each step.
        for step in plan:
            step_name = f'step_{step["step_id"]}'
            steps_status[step_name] = "pending"
            steps_results[step_name] = None

        return execute(plan, steps_status, function_map, steps_results)
    except Exception as e:
        return {"steps_status": steps_status, "steps_results": steps_results}


plan = [
    {
        "step_id": 0,
        "tool": "search_flights",
        "arguments": {
            "from": "Kanpur",
            "to": "Delhi",
            "date": {"day": 25, "month": 10, "year": 2023},
        },
        "depends_on": [],
    },
    {
        "step_id": 1,
        "tool": "search_flights",
        "arguments": {
            "from": "Delhi",
            "to": "Kanpur",
            "date": {"day": 29, "month": 10, "year": 2023},
        },
        "depends_on": [],
    },
    {
        "step_id": 2,
        "tool": "search_hotels",
        "arguments": {
            "check_in": {"day": 25, "month": 10, "year": 2023},
            "check_out": {"day": 29, "month": 10, "year": 2023},
            "city": "Delhi",
        },
        "depends_on": [],
    },
    {
        "step_id": 3,
        "tool": "calculate_cost",
        "arguments": {
            "to_flight_cost": {"result_of": 0},
            "from_flight_cost": {"result_of": 1},
            "hotel_cost": {"result_of": 2},
        },
        "depends_on": [0, 1, 2],
    },
]

print(execute_plan(plan))
