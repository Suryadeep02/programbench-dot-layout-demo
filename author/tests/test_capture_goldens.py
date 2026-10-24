"""Golden capture must fail closed on defective reference observations."""

from pathlib import Path
import sys
import tempfile
import unittest

from author.capture_goldens import capture_case


VALID = "graph 1 0.75 0.5\nnode a 0.375 0.25 0.75 0.5 a solid ellipse black lightgrey\nstop\n"


class CaptureTests(unittest.TestCase):
    def _program(self, source: str) -> list[str]:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        path = Path(temporary.name) / "fake.py"
        path.write_text(source, encoding="utf-8")
        return [sys.executable, str(path)]

    def test_deterministic_complete_plain_is_captured(self):
        command = self._program(f"import sys\nprint({VALID!r},end='')\n")
        self.assertEqual(capture_case(command, "digraph {a}", "plain"), VALID)

    def test_file_input_mode_is_captured(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        dot_path = Path(temporary.name) / "case.dot"
        dot_path.write_text("digraph {a}", encoding="utf-8")
        command = self._program(f"import pathlib,sys\nassert pathlib.Path(sys.argv[-1]).read_text() == 'digraph {{a}}'\nprint({VALID!r},end='')\n")
        self.assertEqual(capture_case(command, "digraph {a}", "plain", input_path=dot_path), VALID)

    def test_nonzero_exit_is_rejected(self):
        command = self._program("import sys\nprint('broken')\nsys.exit(1)\n")
        with self.assertRaises(RuntimeError):
            capture_case(command, "digraph {a}", "plain")

    def test_malformed_output_is_rejected(self):
        command = self._program("print('graph 1 1 1')\n")
        with self.assertRaises(RuntimeError):
            capture_case(command, "digraph {a}", "plain")

    def test_stderr_warning_is_rejected(self):
        command = self._program(f"import sys\nprint({VALID!r},end='')\nprint('warning',file=sys.stderr)\n")
        with self.assertRaises(RuntimeError):
            capture_case(command, "digraph {a}", "plain")


if __name__ == "__main__":
    unittest.main()
