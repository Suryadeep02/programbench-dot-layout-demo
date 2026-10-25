"""Strict semantic comparator for Graphviz plain/plain-ext output.

The geometric tolerance is small and explicit. Record presentation is flexible;
the topology, attributes, control-point sequence, and global drawing frame are not.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
import math


MAX_COORDINATE_ERROR = 0.03
MAX_MEAN_ERROR = 0.01
MAX_OUTPUT_BYTES = 262_144
IMPOSSIBLE_COST = 1_000_000_000.0


@dataclass(frozen=True)
class Node:
    name: str
    geometry: tuple[float, float, float, float]
    attributes: tuple[str, str, str, str, str]


@dataclass(frozen=True)
class Edge:
    identity: tuple[str, str, int, str | None, str, str]
    geometry: tuple[float, ...]


@dataclass(frozen=True)
class Plain:
    graph: tuple[float, float, float]
    nodes: dict[str, Node]
    edges: tuple[Edge, ...]


def _tokens(line: str) -> list[str]:
    """Split a plain record while preserving non-quote backslash escapes."""
    result: list[str] = []
    current: list[str] = []
    quoted = False
    html_depth = 0
    html_quote = False
    active = False
    index = 0
    while index < len(line):
        char = line[index]
        if html_depth:
            current.append(char)
            if char == '"' and (index == 0 or line[index - 1] != "\\"):
                html_quote = not html_quote
            elif not html_quote:
                if char == "<":
                    html_depth += 1
                elif char == ">":
                    html_depth -= 1
            index += 1
            continue
        if not quoted and not active and char == "<":
            current.append(char)
            active = True
            html_depth = 1
            index += 1
            continue
        if quoted and char == "\\" and index + 1 < len(line):
            next_char = line[index + 1]
            if next_char in ('"', "\\"):
                current.append(next_char)
            else:
                current.extend(("\\", next_char))
            index += 2
            continue
        if char == '"':
            quoted = not quoted
            active = True
        elif char.isspace() and not quoted:
            if active:
                result.append("".join(current))
                current.clear()
                active = False
        else:
            current.append(char)
            active = True
        index += 1
    if quoted or html_depth:
        raise ValueError("unterminated quoted or HTML-like token")
    if active:
        result.append("".join(current))
    return result


def _finite(value: str) -> float:
    try:
        number = float(value)
    except ValueError as error:
        raise ValueError(f"invalid number {value!r}") from error
    if not math.isfinite(number):
        raise ValueError("non-finite number")
    return number


def parse_plain(output: str) -> Plain:
    """Parse exactly one complete Graphviz plain stream."""
    if len(output.encode("utf-8")) > MAX_OUTPUT_BYTES:
        raise ValueError("plain output exceeds safety bound")
    graph: tuple[float, float, float] | None = None
    nodes: dict[str, Node] = {}
    edges: list[Edge] = []
    stopped = False
    for line_number, line in enumerate(output.splitlines(), 1):
        tokens = _tokens(line)
        if not tokens:
            continue
        kind = tokens[0]
        if stopped:
            raise ValueError(f"record after stop at line {line_number}")
        if kind == "graph":
            if graph is not None or nodes or edges or len(tokens) != 4:
                raise ValueError("invalid or misplaced graph record")
            graph = tuple(_finite(token) for token in tokens[1:4])
        elif kind == "node":
            if graph is None or len(tokens) != 11:
                raise ValueError("invalid node record")
            name = tokens[1]
            if name in nodes:
                raise ValueError(f"duplicate node {name!r}")
            geometry = tuple(_finite(token) for token in tokens[2:6])
            nodes[name] = Node(name, geometry, tuple(tokens[6:11]))
        elif kind == "edge":
            if graph is None or len(tokens) < 8:
                raise ValueError("invalid edge record")
            try:
                point_count = int(tokens[3])
            except ValueError as error:
                raise ValueError("invalid edge point count") from error
            if point_count < 0 or point_count > 4096 or tokens[3] != str(point_count):
                raise ValueError("invalid edge point count")
            suffix_start = 4 + 2 * point_count
            suffix_length = len(tokens) - suffix_start
            if suffix_length not in (2, 5):
                raise ValueError("edge record has wrong field count")
            geometry = tuple(_finite(token) for token in tokens[4:suffix_start])
            label: str | None = None
            if suffix_length == 5:
                label = tokens[suffix_start]
                geometry += (_finite(tokens[suffix_start + 1]), _finite(tokens[suffix_start + 2]))
            style, color = tokens[-2:]
            identity = (tokens[1], tokens[2], point_count, label, style, color)
            edges.append(Edge(identity, geometry))
        elif kind == "stop":
            if graph is None or len(tokens) != 1:
                raise ValueError("invalid stop record")
            stopped = True
        else:
            raise ValueError(f"unexpected plain record {kind!r}")
    if graph is None or not stopped:
        raise ValueError("missing graph or stop record")
    return Plain(graph, nodes, tuple(edges))


def _differences(expected: tuple[float, ...], actual: tuple[float, ...]) -> list[float]:
    if len(expected) != len(actual):
        raise ValueError("geometry length mismatch")
    return [abs(left - right) for left, right in zip(expected, actual)]


def _minimum_assignment(cost: list[list[float]]) -> list[int]:
    """Hungarian minimum-cost assignment for a square matrix."""
    size = len(cost)
    if size == 0:
        return []
    u = [0.0] * (size + 1)
    v = [0.0] * (size + 1)
    match = [0] * (size + 1)
    path = [0] * (size + 1)
    for row in range(1, size + 1):
        match[0] = row
        column = 0
        min_cost = [math.inf] * (size + 1)
        visited = [False] * (size + 1)
        while True:
            visited[column] = True
            active_row = match[column]
            delta = math.inf
            next_column = 0
            for candidate_column in range(1, size + 1):
                if visited[candidate_column]:
                    continue
                reduced = cost[active_row - 1][candidate_column - 1] - u[active_row] - v[candidate_column]
                if reduced < min_cost[candidate_column]:
                    min_cost[candidate_column] = reduced
                    path[candidate_column] = column
                if min_cost[candidate_column] < delta:
                    delta = min_cost[candidate_column]
                    next_column = candidate_column
            for candidate_column in range(size + 1):
                if visited[candidate_column]:
                    u[match[candidate_column]] += delta
                    v[candidate_column] -= delta
                else:
                    min_cost[candidate_column] -= delta
            column = next_column
            if match[column] == 0:
                break
        while True:
            previous = path[column]
            match[column] = match[previous]
            column = previous
            if column == 0:
                break
    assignment = [-1] * size
    for column in range(1, size + 1):
        assignment[match[column] - 1] = column - 1
    return assignment


def compare_plain(reference: str, candidate: str) -> tuple[bool, list[str]]:
    """Return pass/fail and concise diagnostic differences."""
    expected = parse_plain(reference)
    try:
        actual = parse_plain(candidate)
    except (UnicodeError, ValueError) as error:
        return False, [f"candidate output is invalid: {error}"]
    errors: list[str] = []
    numeric: list[float] = _differences(expected.graph, actual.graph)
    if set(expected.nodes) != set(actual.nodes):
        errors.append("node identity set differs")
    else:
        for name in sorted(expected.nodes):
            left, right = expected.nodes[name], actual.nodes[name]
            if left.attributes != right.attributes:
                errors.append(f"node {name!r} attributes differ")
            numeric.extend(_differences(left.geometry, right.geometry))
    expected_edges: dict[tuple[str, str, int, str | None, str, str], list[Edge]] = defaultdict(list)
    actual_edges: dict[tuple[str, str, int, str | None, str, str], list[Edge]] = defaultdict(list)
    for edge in expected.edges:
        expected_edges[edge.identity].append(edge)
    for edge in actual.edges:
        actual_edges[edge.identity].append(edge)
    if {key: len(group) for key, group in expected_edges.items()} != {key: len(group) for key, group in actual_edges.items()}:
        errors.append("edge identity or multiplicity differs")
    else:
        for key, left_group in expected_edges.items():
            right_group = actual_edges[key]
            cost: list[list[float]] = []
            for left in left_group:
                row: list[float] = []
                for right in right_group:
                    differences = _differences(left.geometry, right.geometry)
                    row.append(sum(differences) if all(d <= MAX_COORDINATE_ERROR + 1e-9 for d in differences) else IMPOSSIBLE_COST)
                cost.append(row)
            for left_index, right_index in enumerate(_minimum_assignment(cost)):
                if cost[left_index][right_index] >= IMPOSSIBLE_COST:
                    errors.append(f"edge geometry differs for {key[:2]}")
                    break
                numeric.extend(_differences(left_group[left_index].geometry, right_group[right_index].geometry))
    if any(difference > MAX_COORDINATE_ERROR + 1e-9 for difference in numeric):
        errors.append("a coordinate exceeds the absolute tolerance")
    if numeric and sum(numeric) / len(numeric) > MAX_MEAN_ERROR + 1e-9:
        errors.append("mean geometric displacement exceeds tolerance")
    return not errors, errors[:8]
