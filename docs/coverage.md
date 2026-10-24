# Requirement-to-verifier map

The released demo suite has **120 cases**, ten in each family, 84 through standard input and 36 through a local file argument. There are 105 `plain` and 15 `plain-ext` cases. All 120 input hashes and all 120 reference output hashes are distinct. The largest graph has 18 nodes and 37 edges. The dense crossing family contains four 15–18-node cases. The historical records report that each golden was captured twice without warnings. The complete suite passed a separate containerized reference replay, 120/120. The historical byte-identity report states that the fully static reference reproduced all frozen outputs on two observations per case. Release-time replay coverage is listed separately in the validation notes.

| Requirement | Cases / evidence | Verifier assertion |
| --- | --- | --- |
| DOT lexical and graph structure | `foundations`, `subgraphs`. Quoted/escaped IDs, comments, defaults, edge chains | exact node set. Exact edge multiset. Labels, style, shape, colors |
| Rank placement and constraints | `rank`, `crossing`, `orientation`, `compound`. Same-rank, `minlen`, `weight`, `constraint`, `ordering`, `group` | graph width/height. Node centers. Each edge's point count and ordered coordinates |
| Node measurement and presentation | `geometry`, `ports`, `compound`. 3 fixed-size, 3 font, 2 HTML-like table-label cases | node dimensions, label token, style, shape, line/fill colors, induced geometry |
| Edge routing and labels | `edge`, `ports`, `cycles`, `clusters`, `compound`. Parallel edges and self-loops | one-to-one edge matching, full control-point sequence, label position and text, style/color |
| Ports and record fields | all 10 `ports` cases plus compound. 3 explicit `headport`/`tailport` attribute cases | complete `plain-ext` endpoint:port identity and path geometry |
| Clusters and compounds | `clusters`, `compound`. 5 nested-cluster cases | cluster-induced graph/node/spline geometry, edge multiplicity and labels |
| Undirected/disconnected graphs | all 10 `components` cases | graph bounds, node layout, `--` edge realization and routing |
| CLI I/O | 84 stdin and 36 local-file cases. Both output flags | exit zero, one complete valid plain stream, no extra records |
| Output safety | all cases plus mutation suite | reject NaN/Infinity, malformed/duplicate/missing records, wrong point count, excess coordinate or mean displacement |

The `evaluator/plain.py` parser requires `graph`, all node and edge records, and a final `stop`. It validates every field. Numeric tolerance is 0.03 inches per field and 0.01 inches mean absolute difference per case. It does not normalize scale, translation, rotation, or spline shape. Parallel indistinguishable edges are assigned one to one by minimum cost. Harmless whitespace and record order changes are accepted.

The following table is retained from recorded calibration checks. Those shortcut runs were not all repeated for this public release.

## Recorded shortcut measurements before calibration

| Candidate / mutation | Passed |
| --- | ---: |
| Pinned reference in sealed grader | 120/120 |
| Source-built no-op | 0/120 |
| One constant golden for every case | 1/120 |
| Oracle topology/styles with all node and edge positions zeroed | 0/120 |
| Oracle node positions and metadata, with every edge replaced by a straight interpolated path | 34/120 |
| Wrapper calling `/opt/reference/dot` in clean image | 0/3 smoke cases |
| Wrapper calling `/usr/bin/dot` in clean image | 0/3 smoke cases |

The 34/120 straight-path result is an **oracle-assisted upper-bound probe**, not a realistic solver score: it retains the exact reference graph bounds, node centers/sizes, labels, styles, edge identities, and label positions. The mutation audit also rejected graph-width shifts, NaN, missing/duplicate nodes and edges, extra records/stops, and missing `stop` on every applicable golden, while accepting semantically equivalent record order on all 120.

These checks exercise specific evaluator failure modes and show a partial-score gradient; they do not establish general soundness or security. Eight independent solver attempts then measured a 24.1% mean, with every attempt completing successfully and the highest scoring 36.7%. See the [validation results](../validation/README.md) for the individual scores.
