"""Capture deterministic private observations from the pinned Linux reference."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess
from typing import Sequence

from evaluator.plain import parse_plain


ROOT = Path(__file__).resolve().parents[1]


def capture_case(command: Sequence[str], dot: str, output_format: str,
                 *, input_path: Path | None = None) -> str:
    if output_format not in ("plain", "plain-ext"):
        raise ValueError(f"unsupported format {output_format!r}")
    environment = dict(os.environ, LC_ALL="C", TZ="UTC")
    observations: list[str] = []
    for _ in range(2):
        try:
            result = subprocess.run(
                [*command, f"-T{output_format}", *([str(input_path)] if input_path else [])],
                input=None if input_path else dot,
                text=True,
                encoding="utf-8",
                errors="strict",
                capture_output=True,
                timeout=15,
                env=environment,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired, UnicodeError) as error:
            raise RuntimeError(f"reference invocation failed: {error}") from error
        if result.returncode != 0:
            raise RuntimeError(f"reference exit {result.returncode}: {result.stderr[:500]}")
        if result.stderr:
            raise RuntimeError(f"reference emitted a warning: {result.stderr[:500]}")
        try:
            parse_plain(result.stdout)
        except ValueError as error:
            raise RuntimeError(f"reference emitted invalid plain text: {error}") from error
        observations.append(result.stdout)
    if observations[0] != observations[1]:
        raise RuntimeError("reference output changed across identical runs")
    return observations[0]


def capture_all(reference: str = "/opt/reference/dot") -> None:
    case_index = ROOT / "evaluator" / "case_index.json"
    golden_dir = ROOT / "evaluator" / "goldens"
    golden_index = ROOT / "evaluator" / "golden_index.json"
    if golden_dir.exists() or golden_index.exists():
        raise FileExistsError("goldens already exist; refusing to overwrite a frozen observation set")
    cases = json.loads(case_index.read_text(encoding="utf-8"))
    if not isinstance(cases, list) or len(cases) != 120:
        raise ValueError("expected exactly 120 indexed cases")
    captured: list[tuple[str, str]] = []
    metadata: list[dict[str, object]] = []
    for case in cases:
        case_id = case["id"]
        source = (ROOT / "evaluator" / "cases" / f"{case_id}.dot").read_text(encoding="utf-8")
        digest = hashlib.sha256(source.encode("utf-8")).hexdigest()
        if digest != case["input_sha256"]:
            raise ValueError(f"input hash changed for {case_id}")
        try:
            observation = capture_case([reference], source, case["format"],
                                       input_path=(ROOT / "evaluator" / "cases" / f"{case_id}.dot")
                                       if case["input_mode"] == "file" else None)
        except RuntimeError as error:
            raise RuntimeError(f"case {case_id}: {error}") from error
        parsed = parse_plain(observation)
        captured.append((case_id, observation))
        metadata.append({
            "id": case_id,
            "output_sha256": hashlib.sha256(observation.encode("utf-8")).hexdigest(),
            "nodes": len(parsed.nodes),
            "edges": len(parsed.edges),
            "bytes": len(observation.encode("utf-8")),
        })
    golden_dir.mkdir()
    for case_id, observation in captured:
        (golden_dir / f"{case_id}.plain").write_text(observation, encoding="utf-8", newline="\n")
    golden_index.write_text(json.dumps(metadata, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"captured {len(captured)} deterministic reference outputs")


if __name__ == "__main__":
    capture_all(os.environ.get("GRAPHVIZ_REFERENCE", "/opt/reference/dot"))
