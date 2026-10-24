"""Run with: python -m unittest discover -s 004-tool-orchestration/03-controller-validation -v"""

from copy import deepcopy
import unittest

from validator import (
    validate_plan,
    PlanStructureError,
    PlanArgumentError,
    PlanDataError,
    PlanDependencyError,
)


# The example supplied by the user. Each test receives its own copy.
EXAMPLE_PLAN = [
    {"step_id": 0, "tool": "search_flights", "arguments": {
        "from": "Kanpur", "to": "Delhi",
        "date": {"day": 25, "month": 10, "year": 2023}}, "depends_on": []},
    {"step_id": 1, "tool": "search_flights", "arguments": {
        "from": "Delhi", "to": "Kanpur",
        "date": {"day": 29, "month": 10, "year": 2023}}, "depends_on": []},
    {"step_id": 2, "tool": "search_hotels", "arguments": {
        "check_in": {"day": 25, "month": 10, "year": 2023},
        "check_out": {"day": 29, "month": 10, "year": 2023},
        "city": "Delhi"}, "depends_on": []},
    {"step_id": 3, "tool": "calculate_cost", "arguments": {
        "to_flight_cost": {"result_of": 0},
        "from_flight_cost": {"result_of": 1},
        "hotel_cost": {"result_of": 2}}, "depends_on": [0, 1, 2]},
]


class ValidatorTests(unittest.TestCase):
    def setUp(self):
        self.plan = deepcopy(EXAMPLE_PLAN)

    def assert_validity(self, plan, expected):
        if expected is True:
            self.assertIs(validate_plan(plan), True)
        else:
            with self.assertRaises(expected) as caught:
                validate_plan(plan)
            self.assertTrue(str(caught.exception))

    def test_supplied_plan(self):
        self.assert_validity(self.plan, True)

    def test_unknown_years(self):
        self.plan[0]["arguments"]["date"]["year"] = None
        self.plan[2]["arguments"]["check_in"]["year"] = None
        self.assert_validity(self.plan, True)

    def test_single_step(self):
        self.assert_validity(self.plan[:1], True)

    def test_literal_costs(self):
        self.plan[3]["arguments"] = {
            "to_flight_cost": 5000, "from_flight_cost": 4500.5, "hotel_cost": None}
        self.plan[3]["depends_on"] = []
        self.assert_validity(self.plan, True)

    def test_nested_result_reference(self):
        self.plan[1]["arguments"]["date"]["year"] = {"result_of": 0}
        self.plan[1]["depends_on"] = [0]
        self.assert_validity(self.plan, True)
        self.plan[1]["depends_on"] = []
        self.assert_validity(self.plan, PlanDependencyError)

    def test_invalid_plan_containers(self):
        for plan in (None, {}, "[]", [], [None], [[]]):
            with self.subTest(plan=plan):
                self.assert_validity(plan, PlanStructureError)

    def test_missing_and_extra_step_fields(self):
        for key in self.plan[0]:
            with self.subTest(missing=key):
                plan = deepcopy(self.plan)
                del plan[0][key]
                self.assert_validity(plan, PlanStructureError)
        self.plan[0]["extra"] = "unexpected"
        self.assert_validity(self.plan, PlanStructureError)

    def test_invalid_step_ids(self):
        for step_id in (-1, 4, True, "0", None, 1):
            with self.subTest(step_id=step_id):
                self.plan[0]["step_id"] = step_id
                self.assert_validity(self.plan, PlanDataError if step_id == 1 and type(step_id) is int else PlanStructureError)

    def test_out_of_order_steps(self):
        self.plan[0], self.plan[1] = self.plan[1], self.plan[0]
        self.assert_validity(self.plan, PlanDataError)

    def test_invalid_tools(self):
        for tool in ("book_flights", None, [], 42):
            with self.subTest(tool=tool):
                self.plan[0]["tool"] = tool
                self.assert_validity(self.plan, PlanStructureError)

    def test_invalid_argument_containers(self):
        for arguments in (None, [], "Kanpur"):
            with self.subTest(arguments=arguments):
                self.plan[0]["arguments"] = arguments
                self.assert_validity(self.plan, PlanStructureError)

    def test_missing_and_extra_arguments(self):
        del self.plan[0]["arguments"]["from"]
        self.assert_validity(self.plan, PlanArgumentError)
        self.plan = deepcopy(EXAMPLE_PLAN)
        self.plan[0]["arguments"]["extra"] = 1
        self.assert_validity(self.plan, PlanArgumentError)

    def test_invalid_nested_arguments(self):
        for date in ({"day": 25}, {"day": 25, "month": 10, "year": 2023, "extra": 1},
                     {"day": "25", "month": 10, "year": 2023},
                     {"day": True, "month": 10, "year": 2023}, []):
            with self.subTest(date=date):
                self.plan[0]["arguments"]["date"] = date
                self.assert_validity(self.plan, PlanArgumentError)

    def test_invalid_string_argument(self):
        self.plan[0]["arguments"]["from"] = 123
        self.assert_validity(self.plan, PlanArgumentError)

    def test_invalid_dependencies(self):
        for dependencies in (None, {}, "0", [0, 0, 1, 2], [-1], [3], [4],
                             [True, 1, 2], ["0", 1, 2], [[]]):
            with self.subTest(dependencies=dependencies):
                self.plan[3]["depends_on"] = dependencies
                self.assert_validity(self.plan, PlanStructureError if type(dependencies) is not list else PlanDependencyError)

    def test_forward_dependency_and_cycle(self):
        self.plan[0]["depends_on"] = [3]
        self.assert_validity(self.plan, PlanDependencyError)

    def test_invalid_result_references(self):
        for reference in ({"result_of": "2"}, {"result_of": True},
                          {"result_of": -1}, {"result_of": 3}, {"result_of": 99},
                          {"result_of": []}, {"result_of": 2, "extra": 1}, {}):
            with self.subTest(reference=reference):
                self.plan[3]["arguments"]["hotel_cost"] = reference
                self.assert_validity(self.plan, PlanDependencyError if type(reference.get("result_of")) is int and set(reference) == {"result_of"} else PlanArgumentError)

    def test_undeclared_result_dependency(self):
        self.plan[3]["depends_on"] = [0, 1]
        self.assert_validity(self.plan, PlanDependencyError)

    def test_validation_does_not_modify_plan(self):
        original = deepcopy(self.plan)
        self.assert_validity(self.plan, True)
        self.assertEqual(self.plan, original)


if __name__ == "__main__":
    unittest.main()
