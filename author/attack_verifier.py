"""Mutate real goldens to probe false-credit paths in the plain comparator."""

from __future__ import annotations

from collections import Counter
import json
from pathlib import Path

from evaluator.plain import compare_plain
from evaluator.run import load_cases


ROOT = Path(__file__).resolve().parents[1]


def _mutations(reference: str) -> dict[str, str]:
    lines = reference.splitlines()
    first = lines[0].split()
    first[2] = str(float(first[2]) + 0.5)
    changed_graph = " ".join(first)
    mutations = {
        "graph-width-shift": "\n".join([changed_graph, *lines[1:]]) + "\n",
        "nan-graph-width": "\n".join([" ".join([first[0], first[1], "nan", *first[3:]]), *lines[1:]]) + "\n",
        "missing-stop": "\n".join(lines[:-1]) + "\n",
        "extra-record": reference + "forged output\n",
        "extra-stop": reference + "stop\n",
    }
    node_index = next((index for index, line in enumerate(lines) if line.startswith("node ")), None)
    if node_index is not None:
        mutations["missing-node"] = "\n".join(lines[:node_index] + lines[node_index + 1:]) + "\n"
        mutations["duplicate-node"] = "\n".join(lines[:node_index] + [lines[node_index]] + lines[node_index:]) + "\n"
    edge_index = next((index for index, line in enumerate(lines) if line.startswith("edge ")), None)
    if edge_index is not None:
        mutations["missing-edge"] = "\n".join(lines[:edge_index] + lines[edge_index + 1:]) + "\n"
        mutations["duplicate-edge"] = "\n".join(lines[:edge_index] + [lines[edge_index]] + lines[edge_index:]) + "\n"
    return mutations


def run_attacks() -> dict[str, int]:
    counts: Counter[str] = Counter()
    for case in load_cases():
        reference = case["golden"]
        if not compare_plain(reference, reference)[0]:
            raise AssertionError(f"reference rejected itself: {case['id']}")
        counts["self-pass"] += 1
        lines = reference.splitlines()
        content = lines[1:-1]
        permuted = "\n".join([lines[0], *reversed(content), lines[-1]]) + "\n"
        if not compare_plain(reference, permuted)[0]:
            raise AssertionError(f"record-order variation rejected: {case['id']}")
        counts["record-order-pass"] += 1
        for name, candidate in _mutations(reference).items():
            if compare_plain(reference, candidate)[0]:
                raise AssertionError(f"{name} earned credit on {case['id']}")
            counts[name + "-rejected"] += 1
    return dict(sorted(counts.items()))


if __name__ == "__main__":
    result = run_attacks()
    (ROOT / "author" / "verifier_attack_result.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, sort_keys=True))
