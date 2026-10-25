"""Optional Docker integration gate, enabled for author verification."""

import os
import unittest

from evaluator.run import score_image


@unittest.skipUnless(os.environ.get("DOT_AGENT_IMAGE"), "set DOT_AGENT_IMAGE for Docker replay")
class DockerReplayTests(unittest.TestCase):
    def test_oracle_handles_file_and_stdin_cases(self):
        result = score_image(os.environ["DOT_AGENT_IMAGE"], "/opt/reference/dot", limit=3)
        self.assertEqual((result["passed"], result["total"]), (3, 3), result["cases"])


if __name__ == "__main__":
    unittest.main()
