"""Optional Docker check for an honest source-only candidate build."""

import os
from pathlib import Path
import subprocess
import tempfile
import unittest
import base64
import zlib

from author.validate_submission import CandidateBuildFailure, build_submission, scan_source
from author.grade_submission import grade


ROOT = Path(__file__).resolve().parents[2]


@unittest.skipUnless(os.environ.get("DOT_CLEANROOM_IMAGE"), "set DOT_CLEANROOM_IMAGE for Docker build")
class CleanroomTests(unittest.TestCase):
    def test_noop_source_builds_without_oracle(self):
        image = os.environ["DOT_CLEANROOM_IMAGE"]
        digest = build_submission(ROOT / "author" / "baselines" / "noop", image)
        self.assertEqual(len(digest), 64)
        result = subprocess.run(
            ["docker", "run", "--rm", "--network", "none", "--read-only", image,
             "sh", "-c", "test -x /workspace/build/dot && test ! -e /opt/reference/dot && ! command -v dot"],
            capture_output=True, text=True, timeout=30, check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_compile_failure_is_zero_score(self):
        with tempfile.TemporaryDirectory() as temporary:
            submission = Path(temporary)
            (submission / "compile.sh").write_text("#!/bin/sh\nexit 7\n", encoding="utf-8")
            result = grade(submission, os.environ["DOT_CLEANROOM_IMAGE"])
            self.assertEqual((result["passed"], result["total"]), (0, 120))
            self.assertTrue(result["build_failure"])

    def test_fragmented_encoded_oracle_is_rejected_after_build(self):
        reference = (ROOT / "agent" / "reference" / "dot").read_bytes()
        encoded = base64.b64encode(zlib.compress(reference, level=9)).decode("ascii")
        with tempfile.TemporaryDirectory() as temporary:
            submission = Path(temporary)
            lines = [encoded[index:index + 100] for index in range(0, len(encoded), 100)]
            quarter = (len(lines) + 3) // 4
            for part in range(4):
                (submission / f"part-{part:02d}.txt").write_text(
                    "\n".join(lines[part * quarter:(part + 1) * quarter]) + "\n",
                    encoding="utf-8", newline="\n")
            (submission / "compile.sh").write_text(
                "#!/bin/sh\nset -eu\nmkdir -p /workspace/build\n"
                "cat /workspace/part-*.txt | base64 -d | "
                "python3 -c 'import sys,zlib;sys.stdout.buffer.write(zlib.decompress(sys.stdin.buffer.read()))' "
                "> /workspace/build/dot\n"
                "chmod 0755 /workspace/build/dot\n", encoding="utf-8", newline="\n")
            self.assertEqual(scan_source(submission), [], "attack must evade the pre-build text scan")
            image = "dot-plain-reconstruction:test-encoded-oracle"
            try:
                with self.assertRaises(CandidateBuildFailure) as failure:
                    build_submission(submission, image)
                self.assertIn("resembles the reference executable", str(failure.exception))
            finally:
                subprocess.run(["docker", "image", "rm", image], capture_output=True,
                               text=True, timeout=30, check=False)

    def test_legitimate_runtime_text_asset_survives_clean_build(self):
        with tempfile.TemporaryDirectory() as temporary:
            submission = Path(temporary)
            (submission / "compile.sh").write_text(
                "#!/bin/sh\nset -eu\nmkdir -p /workspace/build\n"
                "cp /workspace/run.sh /workspace/build/dot\nchmod 0755 /workspace/build/dot\n",
                encoding="utf-8", newline="\n")
            (submission / "run.sh").write_text(
                "#!/bin/sh\ncat /workspace/asset.txt\n", encoding="utf-8", newline="\n")
            (submission / "asset.txt").write_text("asset-ok\n", encoding="utf-8", newline="\n")
            image = "dot-plain-reconstruction:test-runtime-asset"
            try:
                build_submission(submission, image)
                result = subprocess.run(
                    ["docker", "run", "--rm", "--network", "none", "--read-only", image,
                     "/workspace/build/dot", "-Tplain"],
                    capture_output=True, text=True, timeout=30, check=False,
                )
                self.assertEqual((result.returncode, result.stdout), (0, "asset-ok\n"))
            finally:
                subprocess.run(["docker", "image", "rm", image], capture_output=True,
                               text=True, timeout=30, check=False)


if __name__ == "__main__":
    unittest.main()
