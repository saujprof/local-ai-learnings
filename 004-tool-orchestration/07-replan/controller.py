"""Own workflow state and bound replanning; models only classify or plan."""
from copy import deepcopy

from executor import execute_plan
from replanner import analyse_result, build_replan_context, decide_on_replan_or_reply_back, re_plan_trip, review_revised_plan
from validator import validate_plan, PlanValidatorException


def validate_revision(plan, previous, history):
    validate_plan(plan)
    # Keep required actions, provenance, real dependencies and parallelism intact.
    if len(plan) != len(previous):
        raise ValueError("Replanning must preserve required actions")
    for step, old in zip(plan, previous):
        if step["tool"] != old["tool"] or step["depends_on"] != old["depends_on"]:
            raise ValueError("Replanning must preserve tools and dependencies")
        for name, value in old["arguments"].items():
            if isinstance(value, dict) and "result_of" in value:
                if step["arguments"][name] != value:
                    raise ValueError("Replanning must preserve result provenance")
    # Changing unrelated steps does not count as avoiding a failed search.
    for attempt in history:
        for failure in attempt.get("failures", []):
            failed = failure["step"]
            if any(step["tool"] == failed["tool"] and step["arguments"] == failed["arguments"]
                   for step in plan):
                raise ValueError("Revised plan repeats a previously failed search")


def run_workflow(question, plan, max_replans=2):
    validate_plan(plan)
    history = []
    replan_count = 0
    while True:
        result = execute_plan(plan)
        if analyse_result(result)["action"] == "REPLY_BACK":
            return result
        context = build_replan_context(question, result, deepcopy(history))
        history.append(deepcopy({"type": "execution_failure", "plan": plan, "failures": context["failures"]}))
        if replan_count >= max_replans:
            return {"next_action": "REPLY_BACK", "reply_message": "No suitable trip found within the replan limit.", "result": result}
        # Technical errors need a repair or user input, not speculative changes.
        if any(failure["result"] != "NO_RESULT" for failure in context["failures"]):
            return {"next_action": "REPLY_BACK", "reply_message": "A travel search failed. Please try again later.", "result": result}
        decision = decide_on_replan_or_reply_back(context)
        if decision.get("next_action") != "RE_PLAN":
            return {**decision, "result": result}
        history[-1]["decision_reason"] = decision["reason"]
        context["decision_reason"] = decision["reason"]
        while replan_count < max_replans:
            context["attempt_history"] = deepcopy(history)
            replan_count += 1
            try:
                revised = re_plan_trip(context)
                validate_revision(revised, plan, history)
                review = review_revised_plan(context, revised)
            except (PlanValidatorException, ValueError) as error:
                return {"next_action": "REPLY_BACK", "reply_message": "Could not produce a valid alternative trip.", "reason": str(error), "result": result}
            if review["valid"]:
                plan = revised
                break
            history.append(deepcopy({"type": "semantic_rejection", "plan": revised,
                                     "semantic_review": review}))
            context["previous_candidate_plan"] = revised
            context["semantic_feedback"] = review["reason"]
        else:
            return {"next_action": "REPLY_BACK", "reply_message": "Could not produce a coherent alternative within the replan limit.",
                    "reason": context["semantic_feedback"], "result": result}
