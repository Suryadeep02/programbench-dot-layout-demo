"""A valid plain stream gets one vote only after a successful process exit."""

import unittest
from unittest.mock import patch
import subprocess

from evaluator.run import judge_observation, load_cases, run_case_docker, summarize


REFERENCE = "graph 1 0.75 0.5\nnode a 0.375 0.25 0.75 0.5 a solid ellipse black lightgrey\nstop\n"


class RunnerTests(unittest.TestCase):
    def test_successful_complete_observation_passes(self):
        self.assertEqual(judge_observation(REFERENCE, 0, REFERENCE), [])

    def test_nonzero_exit_fails_even_if_stdout_matches(self):
        self.assertTrue(judge_observation(REFERENCE, 2, REFERENCE))

    def test_fabricated_geometry_fails(self):
        self.assertTrue(judge_observation(REFERENCE, 0, REFERENCE.replace("0.375", "9.375")))

    def test_frozen_case_and_golden_hashes_load(self):
        cases = load_cases()
        self.assertEqual(len(cases), 120)
        self.assertEqual(sum(case["input_mode"] == "file" for case in cases), 36)

    def test_flat_percentage(self):
        result = summarize([
            {"id": "one", "family": "a", "passed": True, "differences": []},
            {"id": "two", "family": "a", "passed": False, "differences": ["wrong"]},
            {"id": "three", "family": "b", "passed": True, "differences": []},
        ])
        self.assertEqual((result["passed"], result["total"], result["score"]), (2, 3, 200 / 3))

    def test_file_case_mounts_only_its_own_input_without_network(self):
        case = {"id": "probe", "format": "plain", "input_mode": "file", "dot": "digraph {a->b}"}
        with patch("evaluator.run.subprocess.run", return_value=subprocess.CompletedProcess([], 0, "", "")) as process:
            run_case_docker("candidate:probe", "/workspace/build/dot", case)
        command = process.call_args.args[0]
        mounts = [command[index + 1] for index, token in enumerate(command) if token == "--mount"]
        self.assertEqual(len(mounts), 1)
        self.assertIn("target=/input.dot,readonly", mounts[0])
        self.assertEqual(command[command.index("--network") + 1], "none")
        self.assertEqual(command[command.index("--user") + 1], "10001:10001")
        self.assertIn("--read-only", command)
        self.assertIn("--cap-drop", command)
        self.assertEqual(process.call_args.kwargs["input"], None)
        self.assertEqual(command[-1], "/input.dot")
        self.assertNotIn("/opt/reference/dot", command)

    def test_stdin_case_mounts_no_input_directory(self):
        case = {"id": "probe", "format": "plain-ext", "input_mode": "stdin", "dot": "digraph {a->b}"}
        with patch("evaluator.run.subprocess.run", return_value=subprocess.CompletedProcess([], 0, "", "")) as process:
            run_case_docker("candidate:probe", "/workspace/build/dot", case)
        command = process.call_args.args[0]
        self.assertNotIn("--mount", command)
        self.assertIn("-i", command)
        self.assertEqual(process.call_args.kwargs["input"], case["dot"])
        self.assertEqual(command[-1], "-Tplain-ext")


if __name__ == "__main__":
    unittest.main()
