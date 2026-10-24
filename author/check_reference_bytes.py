"""Inside Linux, require the final static reference to reproduce every frozen golden byte for byte."""

from __future__ import annotations

import json
from pathlib import Path

from author.capture_goldens import capture_case
from evaluator.run import ROOT, load_cases


def check() -> dict:
    cases = load_cases()
    for case in cases:
        path = (ROOT / "evaluator" / "cases" / f"{case['id']}.dot"
                if case["input_mode"] == "file" else None)
        actual = capture_case(["/opt/reference/dot"], case["dot"], case["format"], input_path=path)
        if actual != case["golden"]:
            raise AssertionError(f"static reference changed frozen output: {case['id']}")
    result = {"cases": len(cases), "observations_per_case": 2,
              "all_golden_bytes_identical": True}
    print(json.dumps(result, sort_keys=True))
    return result


if __name__ == "__main__":
    check()
