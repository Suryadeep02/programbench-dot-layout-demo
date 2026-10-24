"""Measure oracle-assisted shortcuts to expose a permissive verifier."""

from __future__ import annotations

from collections import Counter, defaultdict
import json

from evaluator.plain import _tokens, compare_plain
from evaluator.run import load_cases
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _serialize(token: str) -> str:
    if token.startswith("<<") and token.endswith(">>"):
        return token
    if not token or any(character.isspace() or character in '"\\' for character in token):
        return '"' + token.replace("\\", "\\\\").replace('"', '\\"') + '"'
    return token


def _render(lines: list[list[str]]) -> str:
    return "\n".join(" ".join(_serialize(token) for token in line) for line in lines) + "\n"


def _zero_geometry(reference: str) -> str:
    lines = [_tokens(line) for line in reference.splitlines()]
    for tokens in lines:
        if tokens[0] == "node":
            tokens[2:4] = ["0", "0"]
        elif tokens[0] == "edge":
            count = int(tokens[3])
            tokens[4:4 + 2 * count] = ["0"] * (2 * count)
            if len(tokens) == 4 + 2 * count + 5:
                tokens[-4:-2] = ["0", "0"]
    return _render(lines)


def _straight_edges(reference: str) -> str:
    lines = [_tokens(line) for line in reference.splitlines()]
    for tokens in lines:
        if tokens[0] != "edge":
            continue
        count = int(tokens[3])
        if count <= 2:
            continue
        start = tuple(float(value) for value in tokens[4:6])
        end = tuple(float(value) for value in tokens[4 + 2 * (count - 1):4 + 2 * count])
        replacement = []
        for index in range(count):
            t = index / (count - 1)
            replacement.extend(f"{start[axis] * (1 - t) + end[axis] * t:.5f}" for axis in (0, 1))
        tokens[4:4 + 2 * count] = replacement
    return _render(lines)


def measure() -> dict[str, object]:
    cases = load_cases()
    counts: dict[str, Counter[str]] = defaultdict(Counter)
    for name in ("constant-output", "oracle-topology-zero-geometry", "oracle-nodes-straight-edges"):
        counts[name] = Counter()
    constant = cases[0]["golden"]
    for case in cases:
        reference = case["golden"]
        lines = [_tokens(line) for line in reference.splitlines()]
        if not compare_plain(reference, _render(lines))[0]:
            raise AssertionError(f"semantic reserialization failed for {case['id']}")
        for name, candidate in (
            ("constant-output", constant),
            ("oracle-topology-zero-geometry", _zero_geometry(reference)),
            ("oracle-nodes-straight-edges", _straight_edges(reference)),
        ):
            if compare_plain(reference, candidate)[0]:
                counts[name][case["family"]] += 1
    return {name: {"passed": sum(by_family.values()), "total": len(cases),
                   "by_family": dict(sorted(by_family.items()))}
            for name, by_family in sorted(counts.items())}


if __name__ == "__main__":
    result = measure()
    (ROOT / "author" / "baseline_result.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, sort_keys=True))
