"""Exercise concrete oracle, package, encoded-binary, and network shortcuts."""

from __future__ import annotations

import base64
import json
from pathlib import Path
import shutil
import subprocess
import tempfile

from author.validate_submission import build_submission, scan_source
from evaluator.run import score_image


ROOT = Path(__file__).resolve().parents[1]


def run_attacks() -> dict[str, object]:
    matrix: dict[str, object] = {}
    oracle = ROOT / "agent" / "reference" / "dot"
    with tempfile.TemporaryDirectory(prefix="pb-dot-attack-") as temporary:
        submission = Path(temporary)
        (submission / "compile.sh").write_text("#!/bin/sh\nmkdir -p build\n", encoding="utf-8")
        shutil.copy2(oracle, submission / "copied-dot")
        matrix["prebuilt_elf_rejected"] = bool(scan_source(submission))
        (submission / "copied-dot").unlink()
        (submission / "payload.txt").write_text(
            base64.b64encode(oracle.read_bytes()).decode("ascii"), encoding="utf-8")
        matrix["encoded_elf_rejected"] = bool(scan_source(submission))
    for name in ("call_oracle", "call_system_dot"):
        image = f"dot-plain-reconstruction:attack-{name.replace('_', '-')}"
        build_submission(ROOT / "author" / "attacks" / name, image)
        result = score_image(image, "/workspace/build/dot", limit=3)
        matrix[name + "_score"] = f"{result['passed']}/{result['total']}"
        matrix[name + "_blocked"] = result["passed"] == 0
        inventory = subprocess.run(
            ["docker", "run", "--rm", "--network", "none", "--read-only", image,
             "sh", "-c", "test ! -e /opt/reference/dot && test ! -e /usr/bin/dot && "
             "test ! -e /workspace/evaluator/golden_index.json"],
            capture_output=True, text=True, timeout=30, check=False,
        )
        matrix[name + "_image_clean"] = inventory.returncode == 0
    try:
        build_submission(ROOT / "author" / "attacks" / "network_fetch",
                         "dot-plain-reconstruction:attack-network")
    except RuntimeError as error:
        message = str(error)
        matrix["network_build_blocked"] = any(term in message.lower() for term in (
            "name resolution", "network is unreachable", "temporary failure", "urlopen error"))
        matrix["network_build_error_excerpt"] = message[-400:]
    else:
        matrix["network_build_blocked"] = False
    required = [value for key, value in matrix.items() if key.endswith(("_rejected", "_blocked", "_clean"))]
    if not all(required):
        raise AssertionError(f"clean-room attack scored or bypassed isolation: {matrix}")
    return matrix


if __name__ == "__main__":
    result = run_attacks()
    (ROOT / "author" / "cleanroom_attack_result.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, sort_keys=True))
