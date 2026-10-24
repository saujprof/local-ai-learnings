from copy import deepcopy

# Mock tool implementations keep this stage focused on orchestration.
def search_flights(**kwargs):
    from_place = kwargs["from"]
    to_place = kwargs["to"]
    date_of_travel = kwargs["date"]

    print(from_place, to_place)
    print(date_of_travel)

    return 5000


def search_hotels(**kwargs):
    check_in = kwargs["check_in"]
    check_out = kwargs["check_out"]
    city = kwargs["city"]

    print(check_in)
    print(check_out)
    print(city)

    return 9000

def calculate_cost(**kwargs):
    to_flight_cost = kwargs["to_flight_cost"]
    from_flight_cost = kwargs["from_flight_cost"]
    hotel_cost = kwargs["hotel_cost"]

    print(to_flight_cost)
    print(from_flight_cost)
    print(hotel_cost)
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

    # Map the tool name from the plan to the actual Python implementation.
    func = function_map[tool]
    result = func(**tool_args)

    print(result)
    return result


def execute_steps(steps_status, function_map, steps_results, plan):
    """
    Execute all steps currently marked as ready.

    Execution is still sequential in this stage, even when several
    independent steps are ready at the same time.
    """
    for step_name, status in steps_status.items():
        if status == "ready":
            print(f"Execute {step_name}")

            # Convert "step_2" back to numeric step_id 2 and find the
            # corresponding step definition in the validated plan.
            step_id = int(step_name[5:])
            step = [s for s in plan if s["step_id"] == step_id][0]

            result = execute_step(step, function_map, steps_results)

            # Store the real result so dependent steps can use it later.
            steps_results[step_name] = result
            steps_status[step_name] = "done"

def check_dependencies_done(step, steps_status):
    """Check whether all dependencies for a step have completed."""
    for dependency in step["depends_on"]:
        step_name = f"step_{dependency}"

        if steps_status[step_name] != "done":
            return False

    return True


def execute(plan, steps_status, function_map, steps_results):
   
    while not check_all_steps_done(steps_status):
        print(steps_status)
        for step in plan:
            step_name = f'step_{step["step_id"]}'
            if steps_status[step_name] == "done":
                continue
            if steps_status[step_name] == "pending" and check_dependencies_done(step, steps_status):
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
        print(e)
        return False
