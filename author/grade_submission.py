"""Rebuild a source submission in isolation and score the sealed DOT corpus."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from author.validate_submission import CandidateBuildFailure, SourceOnlyFailure, build_submission
from evaluator.run import load_cases, score_image


ROOT = Path(__file__).resolve().parents[1]
EVALUATOR_FILES = (
    "evaluator/case_index.json", "evaluator/golden_index.json",
    "evaluator/plain.py", "evaluator/run.py", "evaluator/Dockerfile.candidate",
    "author/validate_submission.py", "author/grade_submission.py",
)


def evaluator_digest() -> str:
    hasher = hashlib.sha256()
    for name in EVALUATOR_FILES:
        data = (ROOT / name).read_bytes()
        hasher.update(name.encode("utf-8"))
        hasher.update(len(data).to_bytes(8, "big"))
        hasher.update(data)
    return hasher.hexdigest()


def grade(submission: Path, image: str, output: Path | None = None) -> dict:
    before = evaluator_digest()
    candidate_hash = None
    try:
        candidate_hash = build_submission(submission, image)
    except (SourceOnlyFailure, CandidateBuildFailure) as error:
        reason = str(error)[-1000:]
        cases = load_cases()
        result = {"passed": 0, "total": len(cases), "score": 0.0, "partial": False,
                  "cases": [{"id": case["id"], "family": case["family"],
                             "passed": False, "differences": [reason]}
                            for case in cases],
                  "build_failure": reason}
    else:
        result = score_image(image, "/workspace/build/dot")
        result["build_failure"] = None
    if evaluator_digest() != before:
        raise RuntimeError("private evaluator changed during scoring")
    result.update(candidate_sha256=candidate_hash, candidate_image=image,
                  evaluator_sha256=before)
    if output is not None:
        output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"{result['passed']}/{result['total']} ({result['score']:.1f}%)")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("submission", type=Path)
    parser.add_argument("--image", required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    grade(args.submission, args.image, args.output)


if __name__ == "__main__":
    main()
