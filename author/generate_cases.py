"""Generate the private, deterministic DOT corpus once before calibration."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import random


ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class Case:
    id: str
    family: str
    dot: str
    format: str
    input_mode: str
    tags: tuple[str, ...]


def _wrap(name: str, body: str, *, directed: bool = True, strict: bool = False) -> str:
    kind = "digraph" if directed else "graph"
    prefix = "strict " if strict else ""
    return f"{prefix}{kind} {name} {{\n{body}\n}}\n"


def _foundations(index: int) -> tuple[str, str, tuple[str, ...]]:
    bodies = [
        "a;",
        "a; b;",
        "a -> b;",
        "a -> b -> c;",
        "a -> b; a -> c;",
        "a -> c; b -> c;",
        "a -> b; b -> c; a -> c;",
        '"left input" -> "right output"; "right output" -> sink;',
        "node [shape=box]; a -> b; a -> c; c -> d;",
        "graph [label=overview]; a -> b; b -> c; c -> d; a -> d;",
    ]
    return _wrap(f"foundation_{index:02d}", bodies[index], strict=index == 6), "plain", ("basic", "topology")


def _rank(index: int) -> tuple[str, str, tuple[str, ...]]:
    patterns = [
        "a -> b; a -> c; b -> d; c -> d; d -> e;",
        "a -> b; b -> c; c -> d; a -> d [minlen=3]; d -> e;",
        "a -> b; a -> c; b -> d; c -> e; d -> f; e -> f;",
        "a -> b; b -> d; a -> c; c -> d [weight=8]; d -> e; b -> e;",
        "a -> b; b -> c; c -> d; d -> e; a -> e [constraint=false];",
        "a -> b; a -> c; b -> d [minlen=2]; c -> d; d -> e;",
        "a -> b; b -> c; c -> d; a -> d [weight=5]; b -> e; e -> d;",
        "a -> b; a -> c; b -> e; c -> d; d -> e; a -> e [minlen=4];",
        "a -> b; b -> d; a -> c; c -> e; d -> f; e -> f; b -> e [constraint=false];",
        "a -> b; b -> c; c -> d; a -> e; e -> d; b -> f; f -> d [minlen=2];",
    ]
    same = "subgraph { rank=same; b; c; }\n" if index in (2, 3, 5, 8) else ""
    extras = "subgraph { rank=min; a; }\n" if index in (4, 7) else ""
    body = f"node [shape=box];\n{same}{extras}{patterns[index]}"
    return _wrap(f"rank_{index:02d}", body), "plain", ("rank", "constraints", "dag")


def _crossing(index: int) -> tuple[str, str, tuple[str, ...]]:
    rng = random.Random(9101 + index)
    width = (5 + index % 2) if index >= 6 else (3 + index % 2)
    tiers = [[f"{letter}{n}" for n in range(width)] for letter in "abc"]
    lines = ["node [shape=circle,width=0.42,fixedsize=true];"]
    for tier in tiers:
        lines.append("subgraph { rank=same; " + "; ".join(tier) + "; }")
    for source_tier, target_tier in zip(tiers, tiers[1:]):
        for source in source_tier:
            choices = rng.sample(target_tier, 3 if index >= 6 else 2)
            for target in choices:
                lines.append(f"{source} -> {target};")
    if index % 3 == 0:
        lines.append("a0 [ordering=out];")
    if index % 3 == 1:
        lines.append("a1 [group=west]; b1 [group=west]; c1 [group=west];")
    if index >= 5:
        lines.append(f"a{index % width} -> c{(index + 1) % width} [constraint=false];")
    tags = ("crossing", "same-rank")
    if index % 3 == 0:
        tags += ("ordering",)
    if index % 3 == 1:
        tags += ("group",)
    if index >= 6:
        tags += ("dense-crossing",)
    return _wrap(f"cross_{index:02d}", "\n".join(lines)), "plain", tags


def _orientation(index: int) -> tuple[str, str, tuple[str, ...]]:
    direction = ("LR", "RL", "BT", "TB")[index % 4]
    separation = ("0.25", "0.38", "0.52", "0.71", "0.30")[index % 5]
    rank_gap = ("0.55", "0.8", "1.15")[index % 3]
    edges = [
        "start -> load; start -> validate; load -> join; validate -> join; join -> end;",
        "start -> load -> end; start -> validate -> end; load -> validate [constraint=false];",
        "start -> load; load -> validate; validate -> end; start -> end [minlen=3];",
    ][index % 3]
    body = (f"graph [rankdir={direction},nodesep={separation},ranksep={rank_gap}];\n"
            f"node [shape=box];\n{edges}")
    return _wrap(f"orient_{index:02d}", body), "plain", ("orientation", "spacing", "routing")


def _geometry(index: int) -> tuple[str, str, tuple[str, ...]]:
    shapes = ("box", "ellipse", "circle", "diamond", "plaintext", "record")
    shape = shapes[index % len(shapes)]
    label = ('"first\\nsecond"' if index % 3 == 0 else f'"task {index}: verify"')
    if shape == "record":
        label = '"{<left> left|<right> right}"'
    if index in (8, 9):
        shape = "plaintext"
        label = (f'<<TABLE BORDER="0" CELLBORDER="1" CELLSPACING="0">'
                 f'<TR><TD>stage</TD><TD>{index}</TD></TR>'
                 f'<TR><TD COLSPAN="2">verified</TD></TR></TABLE>>')
    fixed = "true" if index in (2, 4, 7) else "false"
    if fixed == "true":
        label = f'"T{index}"'
    width = f"{0.55 + (index % 4) * 0.21:.2f}"
    height = f"{0.34 + (index % 3) * 0.18:.2f}"
    font = ',fontname="Courier",fontsize=14' if index in (5, 8, 9) else ""
    body = (f"graph [nodesep=0.{3 + index % 4},ranksep=0.{6 + index % 3}];\n"
            f"input [shape={shape},label={label},width={width},height={height},fixedsize={fixed},margin=0.08{font}];\n"
            f"worker [shape=box,label=work_{index}]; output [shape=ellipse,label=done];\n"
            "input -> worker; worker -> output;")
    tags = ("node-size", "labels", "shape")
    if index in (8, 9):
        tags += ("html-label",)
    if fixed == "true":
        tags += ("fixed-size",)
    if font:
        tags += ("font",)
    return _wrap(f"geometry_{index:02d}", body), "plain", tags


def _edge(index: int) -> tuple[str, str, tuple[str, ...]]:
    colors = ("red", "blue", "green4", "purple", "black")
    styles = ("solid", "dashed", "dotted", "bold")
    body = ["node [shape=box];", "a -> b;", "a -> c;", "b -> d;", "c -> d;"]
    body.append(f'a -> d [label="path {index}",color={colors[index % 5]},style={styles[index % 4]},minlen={1 + index % 3}];')
    if index % 2 == 0:
        body.append(f'b -> d [label="retry {index}",color=gray40,dir=both,arrowtail=vee];')
    if index % 3 == 1:
        body.append("c -> a [constraint=false,style=dotted,dir=none];")
    if index >= 6:
        body.append("d -> e [label=finish,arrowhead=diamond];")
    tags = ("edge-label", "spline") + (("parallel",) if index % 2 == 0 else ())
    return _wrap(f"edge_{index:02d}", "\n".join(body)), "plain", tags


def _ports(index: int) -> tuple[str, str, tuple[str, ...]]:
    left_port = ("out", "mid", "in")[index % 3]
    right_port = ("in", "mid")[index % 2]
    compass = ":e" if index % 2 == 0 else ":s"
    body = [
        'source [shape=record,label="{<in> ingest|<mid> inspect|<out> emit}"];',
        'transform [shape=record,label="{<in> receive|<mid> change|<out> release}"];',
        'sink [shape=record,label="{<in> store|<out> notify}"];',
        f"source:{left_port}{compass} -> transform:{right_port}:w [label=flow_{index}];",
        "transform:out -> sink:in;",
    ]
    if index % 3 == 2:
        body.append("source:mid -> sink:in [constraint=false,color=blue];")
    if index >= 5:
        body.append("transform:mid -> transform:in [label=retry];")
    if index % 4 == 3:
        body.append("graph [rankdir=LR];")
    if index >= 7:
        body.append('source -> sink [tailport="out:e",headport="in:w",style=dashed];')
    tags = ("ports", "record", "routing") + (("attribute-port",) if index >= 7 else ())
    return _wrap(f"ports_{index:02d}", "\n".join(body)), "plain-ext", tags


def _subgraphs(index: int) -> tuple[str, str, tuple[str, ...]]:
    names = ("alpha one", "beta two", "gamma three", "delta four")
    first = names[index % 4]
    second = names[(index + 1) % 4]
    body = [
        "node [shape=box,color=gray30];",
        f'subgraph stage_a {{ node [color=blue]; "{first}"; "{second}"; "{first}" -> "{second}"; }}',
        f'subgraph stage_b {{ node [shape=ellipse]; final_{index}; audit_{index}; final_{index} -> audit_{index}; }}',
        f'"{second}" -> final_{index} -> sink [label=handoff];',
    ]
    if index % 2 == 0:
        body.append(f'subgraph {{ rank=same; "{second}"; final_{index}; }}')
    if index % 3 == 0:
        body.append(f'edge [color=purple]; audit_{index} -> sink;')
    if index >= 6:
        body.append('"quoted end" [shape=diamond]; sink -> "quoted end";')
    if index >= 7:
        body.append(r'"say \"go\"" -> sink;')
    if index == 9:
        body.append("// A comment between semantic statements must be ignored.")
    tags = ("subgraph", "defaults", "quoted-id") + (("escaped-quote",) if index >= 7 else ())
    return _wrap(f"subgraph_{index:02d}", "\n".join(body)), "plain", tags


def _clusters(index: int) -> tuple[str, str, tuple[str, ...]]:
    direction = "LR" if index % 2 else "TB"
    compute = (f'subgraph cluster_compute {{ label="compute {index}"; '
               'subgraph cluster_inner { label="inner"; worker; validate; worker -> validate; } }'
               if index >= 5 else
               f'subgraph cluster_compute {{ label="compute {index}"; worker; validate; worker -> validate; }}')
    body = [
        f"graph [compound=true,rankdir={direction}];",
        "node [shape=box];",
        f'subgraph cluster_ingest {{ label="ingest {index}"; api; queue; api -> queue; }}',
        compute,
        "queue -> worker [ltail=cluster_ingest,lhead=cluster_compute];",
        "validate -> result;",
    ]
    if index % 3 == 0:
        body.append('subgraph cluster_review { label="review"; check; approve; check -> approve; }')
        body.append("validate -> check [lhead=cluster_review]; approve -> result [ltail=cluster_review];")
    if index % 3 == 1:
        body.append("api -> validate [constraint=false,color=gray50];")
    if index >= 6:
        body.append('subgraph cluster_store { label="storage"; result; archive; result -> archive; }')
    tags = ("cluster", "compound-edge", "routing") + (("nested-cluster",) if index >= 5 else ())
    return _wrap(f"cluster_{index:02d}", "\n".join(body)), "plain", tags


def _cycles(index: int) -> tuple[str, str, tuple[str, ...]]:
    count = 3 + index % 5
    nodes = [f"n{number}" for number in range(count)]
    body = ["node [shape=circle,width=0.45,fixedsize=true];"]
    body.extend(f"{nodes[n]} -> {nodes[(n + 1) % count]};" for n in range(count))
    body.append(f"{nodes[-1]} -> {nodes[1]} [constraint=false,color=red];")
    if index % 2 == 0:
        body.append(f"{nodes[1]} -> {nodes[1]} [label=again];")
    if index % 3 == 0:
        body.append(f"{nodes[0]} -> {nodes[1]} [label=alternate,style=dashed];")
    if index >= 5:
        body.append(f"{nodes[0]} -> extra; extra -> {nodes[-2]};")
    tags = ("cycle",) + (("self-loop",) if index % 2 == 0 else ())
    tags += (("multiedge",) if index % 3 == 0 else ())
    return _wrap(f"cycle_{index:02d}", "\n".join(body)), "plain", tags


def _components(index: int) -> tuple[str, str, tuple[str, ...]]:
    body = ["node [shape=ellipse];", "a -- b -- c;", "x -- y;"]
    if index % 2 == 0:
        body.append("lonely;")
    if index % 3 == 0:
        body.append("p -- q -- r -- p;")
    if index % 3 == 1:
        body.append("c -- x [style=dashed];")
    if index >= 5:
        body.append(f'"separate {index}" -- orphan_{index} [label=link];')
    if index % 4 == 3:
        body.append("graph [rankdir=LR,nodesep=0.45];")
    return _wrap(f"component_{index:02d}", "\n".join(body), directed=False), "plain", ("undirected", "components", "packing")


def _compound(index: int) -> tuple[str, str, tuple[str, ...]]:
    direction = ("LR", "TB", "BT")[index % 3]
    body = [
        f"graph [compound=true,rankdir={direction},nodesep=0.{3 + index % 4}];",
        "node [shape=box,style=rounded];",
        f'subgraph cluster_intake {{ label="Intake {index}"; request [shape=record,label="{{<raw> raw|<ok> accepted}}"]; parse; request:ok -> parse; }}',
        'subgraph cluster_checks { label="Checks"; schema; policy; audit; schema -> audit; policy -> audit; }',
        'subgraph cluster_delivery { label="Delivery"; queue; worker; store; queue -> worker -> store; }',
        'parse -> schema [ltail=cluster_intake,lhead=cluster_checks,label=structure];',
        'parse -> policy [label=permission];',
        'audit -> queue [ltail=cluster_checks,lhead=cluster_delivery,label=commit];',
        'worker -> policy [constraint=false,color=gray50,style=dashed];',
        'store -> notify [label=complete];',
    ]
    if index % 2 == 0:
        body.append("schema -> policy [constraint=false,color=gray60];")
    if index % 3 == 0:
        body.append("audit -> reject [label=invalid,color=red];")
    if index % 4 == 1:
        body.append('worker -> worker [label="retry",color=orange];')
    if index >= 6:
        body.append('subgraph cluster_observe { label="Observability"; metrics; log; metrics -> log; }')
        body.append("worker -> metrics [lhead=cluster_observe,constraint=false];")
    tags = ("workflow", "cluster", "record-port", "labels", "cycles", "rank")
    return _wrap(f"workflow_{index:02d}", "\n".join(body)), ("plain-ext" if index % 2 else "plain"), tags


FAMILY_BUILDERS = (
    ("foundations", _foundations),
    ("rank", _rank),
    ("crossing", _crossing),
    ("orientation", _orientation),
    ("geometry", _geometry),
    ("edge", _edge),
    ("ports", _ports),
    ("subgraphs", _subgraphs),
    ("clusters", _clusters),
    ("cycles", _cycles),
    ("components", _components),
    ("compound", _compound),
)


def build_cases() -> list[Case]:
    cases: list[Case] = []
    for family, builder in FAMILY_BUILDERS:
        for index in range(10):
            dot, output_format, tags = builder(index)
            input_mode = "file" if index % 4 == 0 else "stdin"
            cases.append(Case(f"{family}-{index:02d}", family, dot, output_format, input_mode, tags))
    return cases


def write_cases() -> None:
    case_dir = ROOT / "evaluator" / "cases"
    manifest = ROOT / "evaluator" / "case_index.json"
    if case_dir.exists() or manifest.exists():
        raise FileExistsError("private cases already exist; refusing to overwrite frozen fixtures")
    cases = build_cases()
    case_dir.mkdir(parents=True)
    index = []
    for case in cases:
        (case_dir / f"{case.id}.dot").write_text(case.dot, encoding="utf-8", newline="\n")
        index.append({
            "id": case.id,
            "family": case.family,
            "format": case.format,
            "input_mode": case.input_mode,
            "tags": list(case.tags),
            "input_sha256": hashlib.sha256(case.dot.encode("utf-8")).hexdigest(),
        })
    manifest.write_text(json.dumps(index, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"generated {len(cases)} private cases")


if __name__ == "__main__":
    write_cases()
