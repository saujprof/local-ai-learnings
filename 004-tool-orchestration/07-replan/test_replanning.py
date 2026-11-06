import unittest
from copy import deepcopy
from unittest.mock import patch

import controller
from executor import plan as example_plan
from replanner import analyse_result, build_replan_context


def failed_result(plan):
    return {"plan": plan,
            "steps_status": {"step_0": "done", "step_1": "done", "step_2": "failed", "step_3": "pending"},
            "steps_results": {"step_0": 5000, "step_1": 5000, "step_2": "NO_RESULT", "step_3": None}}


def shifted(plan):
    revised = deepcopy(plan)
    revised[0]["arguments"]["date"]["day"] -= 1
    revised[1]["arguments"]["date"]["day"] -= 1
    revised[2]["arguments"]["check_in"]["day"] -= 1
    revised[2]["arguments"]["check_out"]["day"] -= 1
    return revised


class ReplanningTests(unittest.TestCase):
    def test_normalized_context(self):
        result = failed_result(example_plan)
        self.assertEqual(analyse_result(result), {"action": "TAKE_DECISION"})
        context = build_replan_context("around 25th", result, [])
        self.assertEqual(len(context["successful_steps"]), 2)
        self.assertEqual(context["failed_result"], "NO_RESULT")
        self.assertEqual(context["pending_steps"], [example_plan[3]])

    def test_revision_guards(self):
        history = [{"failures": [{"step": example_plan[2], "result": "NO_RESULT"}]}]
        revised = shifted(example_plan)
        controller.validate_revision(revised, example_plan, history)
        with self.assertRaises(ValueError):
            controller.validate_revision(example_plan, revised, history)
        revised[3]["arguments"]["hotel_cost"] = 0
        with self.assertRaises(ValueError):
            controller.validate_revision(revised, example_plan, history)

    @patch.object(controller, "decide_on_replan_or_reply_back", return_value={"next_action": "RE_PLAN", "reason": "Dates flexible"})
    @patch.object(controller, "execute_plan", side_effect=failed_result)
    @patch.object(controller, "review_revised_plan", return_value={"valid": True, "reason": ""})
    def test_history_limit_and_local_counter(self, review, execute, decide):
        with patch.object(controller, "re_plan_trip", side_effect=[shifted(example_plan), shifted(shifted(example_plan))]) as replan:
            result = controller.run_workflow("around 25th", example_plan)
            self.assertEqual(result["next_action"], "REPLY_BACK")
            self.assertEqual(execute.call_count, 3)
            self.assertEqual(len(replan.call_args.args[0]["attempt_history"]), 2)
        with patch.object(controller, "re_plan_trip", return_value=shifted(example_plan)) as replan:
            controller.run_workflow("around 25th", example_plan, max_replans=1)
            self.assertEqual(replan.call_count, 1)

    @patch.object(controller, "decide_on_replan_or_reply_back", return_value={"next_action": "RE_PLAN", "reason": "Dates flexible"})
    @patch.object(controller, "execute_plan", side_effect=failed_result)
    def test_semantic_feedback_and_shared_budget(self, execute, decide):
        rejected = shifted(example_plan)
        repaired = shifted(rejected)
        feedback = {"valid": False, "reason": "Trip dates conflict"}
        with patch.object(controller, "re_plan_trip", side_effect=[rejected, repaired]) as replan, patch.object(
                controller, "review_revised_plan", side_effect=[feedback, {"valid": True, "reason": ""}]):
            controller.run_workflow("around 25th", example_plan)
            self.assertEqual(execute.call_count, 2)
            self.assertEqual(execute.call_args.args[0], repaired)
            context = replan.call_args.args[0]
            self.assertEqual(context["previous_candidate_plan"], rejected)
            self.assertEqual(context["semantic_feedback"], feedback["reason"])
            self.assertEqual([item["type"] for item in context["attempt_history"]],
                             ["execution_failure", "semantic_rejection"])
        execute.reset_mock()
        with patch.object(controller, "re_plan_trip", return_value=rejected) as replan, patch.object(
                controller, "review_revised_plan", return_value=feedback):
            result = controller.run_workflow("around 25th", example_plan)
            self.assertEqual(replan.call_count, 2)
            self.assertEqual(execute.call_count, 1)
            self.assertEqual(result["reason"], feedback["reason"])

    def test_malformed_semantic_response(self):
        from replanner import review_revised_plan
        context = build_replan_context("around 25th", failed_result(example_plan), [])
        with patch("replanner.requests.post") as post:
            post.return_value.json.return_value = {"message": {"content": '{"valid": "true", "reason": ""}'}}
            with self.assertRaises(ValueError):
                review_revised_plan(context, shifted(example_plan))

    @patch.object(controller, "re_plan_trip")
    @patch.object(controller, "decide_on_replan_or_reply_back", return_value={"next_action": "REPLY_BACK", "reason": "Strict dates", "reply_message": "No rooms available."})
    @patch.object(controller, "execute_plan", side_effect=failed_result)
    def test_reply_does_not_replan(self, execute, decide, replan):
        controller.run_workflow("on 25th", example_plan)
        replan.assert_not_called()


if __name__ == "__main__":
    unittest.main()
