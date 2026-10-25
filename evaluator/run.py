"""Grade the source-reconstructed dot in isolated one-case containers."""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
import uuid

from evaluator.plain import compare_plain, parse_plain


ROOT = Path(__file__).resolve().parents[1]
TIMEOUT_SECONDS = 10
RUN_SCRIPT = (
    'ulimit -f 1024; '
    'timeout --signal=TERM --kill-after=1s 10s "$@" > /tmp/plain.out 2> /tmp/plain.err; '
    'result=$?; cat /tmp/plain.out; cat /tmp/plain.err >&2; exit "$result"'
)


def load_cases() -> list[dict]:
    index = json.loads((ROOT / "evaluator" / "case_index.json").read_text(encoding="utf-8"))
    goldens = json.loads((ROOT / "evaluator" / "golden_index.json").read_text(encoding="utf-8"))
    if len(index) != 120 or len(goldens) != 120:
        raise ValueError("fixture or golden count changed")
    if len({entry["id"] for entry in index}) != 120:
        raise ValueError("duplicate fixture id")
    golden_by_id = {entry["id"]: entry for entry in goldens}
    if len(golden_by_id) != 120 or set(golden_by_id) != {entry["id"] for entry in index}:
        raise ValueError("golden identity set differs from fixtures")
    if Counter(entry["family"] for entry in index) != {family: 10 for family in (
        "foundations", "rank", "crossing", "orientation", "geometry", "edge",
        "ports", "subgraphs", "clusters", "cycles", "components", "compound",
    )}:
        raise ValueError("fixture family distribution changed")
    if Counter(entry["input_mode"] for entry in index) != {"stdin": 84, "file": 36}:
        raise ValueError("fixture input-mode distribution changed")
    cases = []
    for entry in index:
        case_id = entry["id"]
        if not case_id.replace("-", "").isalnum() or entry["format"] not in ("plain", "plain-ext"):
            raise ValueError(f"invalid case metadata for {case_id}")
        dot = (ROOT / "evaluator" / "cases" / f"{case_id}.dot").read_text(encoding="utf-8")
        reference = (ROOT / "evaluator" / "goldens" / f"{case_id}.plain").read_text(encoding="utf-8")
        if hashlib.sha256(dot.encode("utf-8")).hexdigest() != entry["input_sha256"]:
            raise ValueError(f"input hash changed for {case_id}")
        if hashlib.sha256(reference.encode("utf-8")).hexdigest() != golden_by_id[case_id]["output_sha256"]:
            raise ValueError(f"golden hash changed for {case_id}")
        parsed = parse_plain(reference)
        if (len(parsed.nodes), len(parsed.edges)) != (golden_by_id[case_id]["nodes"], golden_by_id[case_id]["edges"]):
            raise ValueError(f"golden structure changed for {case_id}")
        cases.append({**entry, "dot": dot, "golden": reference})
    return cases


def judge_observation(reference: str, returncode: int, stdout: str) -> list[str]:
    if returncode != 0:
        return [f"candidate exited {returncode}"]
    passed, differences = compare_plain(reference, stdout)
    return [] if passed else differences


def run_case_docker(image: str, executable: str, case: dict) -> tuple[int, str, str]:
    """Give the container one DOT input, no oracle, private metadata, or network."""
    container_name = "dot-case-" + uuid.uuid4().hex[:16]
    with tempfile.TemporaryDirectory(prefix="pb-dot-input-") as temporary:
        docker = [
            "docker", "run", "--rm", "-i", "--name", container_name,
            "--network", "none", "--read-only", "--cap-drop", "ALL",
            "--security-opt", "no-new-privileges", "--pids-limit", "64",
            "--memory", "512m", "--cpus", "1", "--user", "10001:10001",
            "--tmpfs", "/tmp:rw,nosuid,nodev,size=64m",
            "-e", "LC_ALL=C", "-e", "TZ=UTC", "-e", "HOME=/tmp",
            "-e", "PYTHONDONTWRITEBYTECODE=1",
        ]
        if case["input_mode"] == "file":
            input_path = Path(temporary) / "input.dot"
            with input_path.open("w", encoding="utf-8", newline="\n") as handle:
                handle.write(case["dot"])
            docker += ["--mount", f"type=bind,source={input_path.resolve()},target=/input.dot,readonly"]
            stdin = None
            file_argument = ["/input.dot"]
        else:
            stdin = case["dot"]
            file_argument = []
        docker += [image, "sh", "-c", RUN_SCRIPT, "sh", executable,
                   f"-T{case['format']}", *file_argument]
        try:
            result = subprocess.run(docker, input=stdin, capture_output=True,
                                    text=True, encoding="utf-8", errors="replace",
                                    timeout=TIMEOUT_SECONDS + 60, check=False)
        except subprocess.TimeoutExpired as error:
            subprocess.run(["docker", "rm", "-f", container_name], capture_output=True,
                           timeout=15, check=False)
            raise RuntimeError(f"Docker startup/shutdown stalled for {case['id']}") from error
    if result.returncode == 125 and (result.stderr.startswith("docker:") or "Error response from daemon" in result.stderr):
        raise RuntimeError(f"Docker infrastructure failed: {result.stderr[:500]}")
    return result.returncode, result.stdout, result.stderr


def summarize(records: list[dict]) -> dict:
    passed = sum(bool(record["passed"]) for record in records)
    total = len(records)
    return {"passed": passed, "total": total,
            "score": 100.0 * passed / total if total else 0.0,
            "cases": records}


def score_image(image: str, executable: str, *, limit: int | None = None) -> dict:
    cases = load_cases()
    if limit is not None:
        if limit < 1 or limit > len(cases):
            raise ValueError("limit must select at least one existing case")
        cases = cases[:limit]
    records = []
    for case in cases:
        returncode, stdout, _stderr = run_case_docker(image, executable, case)
        differences = judge_observation(case["golden"], returncode, stdout)
        records.append({"id": case["id"], "family": case["family"],
                        "passed": not differences, "differences": differences})
    result = summarize(records)
    result["partial"] = limit is not None
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--image", required=True)
    parser.add_argument("--executable", default="/workspace/build/dot")
    parser.add_argument("--limit", type=int, help="author-only partial smoke run")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = score_image(args.image, args.executable, limit=args.limit)
    rendered = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(rendered, encoding="utf-8")
        print(f"{result['passed']}/{result['total']} ({result['score']:.1f}%) -> {args.output}")
    else:
        print(rendered)


if __name__ == "__main__":
    main()
