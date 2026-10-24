"""A candidate failure is a zero score, not an evaluator crash."""

from pathlib import Path
import tempfile
import unittest

from author.grade_submission import grade


class GradeTests(unittest.TestCase):
    def test_rejected_source_receives_zero_of_all_cases(self):
        with tempfile.TemporaryDirectory() as temporary:
            submission = Path(temporary)
            (submission / "compile.sh").write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
            (submission / "payload").write_bytes(b"\x7fELF" + b"\x00" * 10)
            output = submission / "result.json"
            result = grade(submission, "dot-plain-reconstruction:never-built", output)
            self.assertEqual((result["passed"], result["total"], result["score"]), (0, 120, 0.0))
            self.assertTrue(result["build_failure"])
            self.assertTrue(output.is_file())


if __name__ == "__main__":
    unittest.main()
