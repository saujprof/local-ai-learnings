from tools import search_flights, search_hotels, calculate_cost

tools = [search_hotels, search_flights, calculate_cost]

tools_names = [ tool["function"]["name"] for tool in tools]

class PlanValidatorException(Exception):
    pass

class PlanStructureError(PlanValidatorException):
    pass

class PlanArgumentError(PlanValidatorException):
    pass

class PlanDataError(PlanValidatorException):
    pass

class PlanDependencyError(PlanValidatorException):
    pass

def validate_plan_structure(plan):
    if type(plan) != list:
        raise PlanStructureError("Structure error: plan is not list")

    total_steps = len(plan)
    if total_steps == 0:
        raise PlanStructureError("Structure error: plan is empty")

    for action in plan:
        if type(action) != dict:
            raise PlanStructureError("Structure error: action is not a dictionary")
        if set(action) != {"step_id", "tool", "arguments", "depends_on"}:
            raise PlanStructureError("Structure error: action fields not valid")
        if "step_id" not in action or type(action["step_id"]) != int or action["step_id"] < 0 or action["step_id"] >= total_steps:
            raise PlanStructureError("Structure error: step_id not valid")
        if "tool" not in action or type(action["tool"]) != str or action["tool"] not in tools_names:
            raise PlanStructureError("Structure error: tool not valid")
        if "arguments" not in action or type(action["arguments"]) != dict:
            raise PlanStructureError("Structure error: arguments not valid")
        if "depends_on" not in action or type(action["depends_on"]) != list:
            raise PlanStructureError("Structure error: depends_on not valid")

    return True

def validate_plan_step_ids(plan):
    visited = set()

    for index, action in enumerate(plan):
        if action["step_id"] in visited or action["step_id"] != index:
            raise PlanDataError("Data error: step id not valid")
        visited.add(action["step_id"])

    return True

def validate_tool_args(plan):
    def validate_argument(value, expected):
        # The planner uses null for information the user has not supplied.
        if value is None:
            return True
        if type(value) == dict and "result_of" in value:
            return set(value) == {"result_of"} and type(value["result_of"]) == int
        if type(expected) == dict:
            if type(value) != dict or set(value) != set(expected):
                return False
            return all(validate_argument(value[key], expected[key]) for key in expected)
        if expected == "string":
            return type(value) == str
        if expected == "number":
            return type(value) in (int, float)
        return False

    for action in plan:
        tool = next(tool for tool in tools if tool["function"]["name"] == action["tool"])
        parameters = tool["function"]["parameters"]
        arguments = action["arguments"]
        if set(arguments) != set(parameters):
            raise PlanArgumentError(f"Argument error: parameter names not valid for step {action['step_id']}")
        for name, expected in parameters.items():
            if not validate_argument(arguments[name], expected):
                raise PlanArgumentError(f"Argument error: {name} not valid for step {action['step_id']}")

    return True

def validate_steps_dependecny(plan):
    # Earlier-step dependencies also rule out self-dependencies and cycles.
    for action in plan:
        visited = set()
        for dependency in action["depends_on"]:
            if type(dependency) != int or dependency < 0 or dependency >= action["step_id"]:
                raise PlanDependencyError("Dependency error: dependency must refer to an earlier step")
            if dependency in visited:
                raise PlanDependencyError("Dependency error: duplicate dependency")
            visited.add(dependency)

    return True

def validate_result_dependency(plan):
    def validate_reference(value, action):
        if type(value) == dict:
            if "result_of" in value:
                reference = value["result_of"]
                return (
                    set(value) == {"result_of"}
                    and type(reference) == int
                    and 0 <= reference < action["step_id"]
                    and reference in action["depends_on"]
                )
            return all(validate_reference(nested, action) for nested in value.values())
        if type(value) == list:
            return all(validate_reference(nested, action) for nested in value)
        return True

    for action in plan:
        if not validate_reference(action["arguments"], action):
            raise PlanDependencyError(f"Result error: invalid or undeclared result reference in step {action['step_id']}")

    return True


def validate_plan(plan):
    """Return True for a valid plan; otherwise raise a PlanValidatorException."""
    validate_plan_structure(plan)
    validate_plan_step_ids(plan)
    validate_tool_args(plan)
    validate_steps_dependecny(plan)
    validate_result_dependency(plan)

    return True
