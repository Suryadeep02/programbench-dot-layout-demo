# Adversarial design audit

This checklist describes the original calibration controls and their intended checks. It is not a proof of sandbox security. The corpus is public in this demo, so secrecy-based protections below no longer prevent memorization. Eight saved attempts provide limited calibration evidence, not a general difficulty guarantee.

| Shortcut or failure | Countermeasure / audit |
| --- | --- |
| Invoke system `dot`, `libgvc`, language bindings, or a package downloaded at grade time | Minimal offline candidate build/runtime images. Enumerate executables, packages, shared objects, Python/Node modules, caches, and environment paths. Run a candidate that probes these names and require failure. |
| Carry over the reference ELF or a copied/disassembled implementation | Grade source in a clean container, not the attempt container. Submission allowlist rejects ELF/archives/opaque encoded payloads. Inspect size, magic bytes, base64/hex blobs, object files, symlinks, and generated executable provenance. A source-level reimplementation is allowed. |
| Copy implementation through dynamic dependencies or plugins | Link all Graphviz implementation libraries and plugins into the reference executable. `readelf`/`ldd` plus filesystem/image inventory check for no readable `libgvc`, `libcgraph`, `libpathplan`, `libgvplugin*`, source tree, or secondary `dot`. If this cannot be achieved, reject Graphviz. |
| Inject a solver-built `LD_PRELOAD` library into the execute-only reference, then dump its own code memory | Require a fully static ELF with no `PT_INTERP` program header. Check this in the build and final image audit. `author/probe_reference_isolation.py` requires the final image to block this injection. |
| Read execute-only reference memory through `ptrace` or `/proc/<pid>/mem` | `author/probe_reference_isolation.py` runs a controlled same-user `PTRACE_ATTACH` and requires `EPERM`. Retain root ownership and mode `0111` for the final reference. |
| Query the oracle or private cases while grading | Candidate container has no oracle, golden, fixture generator, author volume, host Docker socket, or network. Mount exactly one input case or pass DOT on stdin. Check mounts, process environment, DNS/network attempts, and filesystem listings from inside a malicious candidate. |
| Memorize sample outputs or use a fixture fingerprint table | Original calibration only: keep scored fixtures private. This public demo does not satisfy that secrecy assumption. Derive many distinct topology/attribute combinations. Use holdout seeds and check uniqueness of normalized DOT and reference output hashes. Examples never coincide with scored inputs. |
| Output only the input topology, arbitrary centers, or straight edges | Plain comparator checks graph scale, node coordinates/dimensions, all edge control points and labels, not just graph structure. Include crossing, bends, ports, and label displacement cases. Run targeted dummy renderers and record their score by family. |
| Exploit tolerance with extreme values or missing records | Parse finite numbers and complete records. Reject NaN/Infinity, truncation, extra lines, duplicate nodes, wrong edge counts, wrong point counts, and strings in numeric fields. Cap both per-coordinate and total displacement. Mutation probes must fail. |
| Exploit ambiguous parallel-edge matching | Partition by endpoint and optional ports, then require one-to-one minimum-cost matching across complete edge records. Check all matched edges against the same tolerances. Include near-identical multiedges. |
| Trigger comparator exceptions or timeout and receive credit | Each case returns pass only after all checks. Parser errors, exceptions, signal exits, timeout, and nonzero exit are zero for that case. Evaluator smoke tests include malformed candidate output and hung candidates. |
| Exploit DOT quoting, escaped names, or output tokenization | Use a documented plain tokenizer compatible with quoted strings and escapes. Include IDs and labels with spaces, punctuation, and escaped quotes. Parser unit tests cover such records. |
| Reuse unpinned fonts or rely on platform drift to make task impossible | Pin runtime image digest, architecture, locale, fonts, Graphviz release hash, and CLI flags. Repeat reference runs and compare goldens byte-for-byte. Remove unstable cases. Give agents version-matched font/format information. |
| Win with only easy parsing cases | Reserve the vast majority of scoring for layout cases. Enumerate each family and feature interaction. Run structural-only and oracle-assisted exact-node/straight-edge baselines. If either exceeds the target, revise before frontier calibration. |
| Make the task effectively impossible or dominated by minute coordinates | Publish numeric tolerance and feature scope. Include a visible learning curve from one-node to multi-feature graphs. Measure reference drift and partial baseline scores. Human review checks cases for meaningful behavior. |
| Hide a known complete implementation in docs or image | Inventory image layers/files, installed packages, docs snippets, build cache and shell history. Scan for Graphviz source signatures. Docs may describe semantics but contain no implementation or goldens. |
| Let authors accidentally grade against a different binary/configuration | Record source tar SHA256, built binary SHA256, toolchain/image digests, `dot -V`, golden manifest hash, and evaluator hash. Regenerate all goldens after any reference/configuration change. |
| Build or submission script executes untrusted code with author secrets | Treat submissions as hostile. Isolated container, no secrets, read-only input, bounded CPU/memory/time, no network, no privileged mounts. |

## Original calibration checklist

1. Official provenance and license are recorded, and the static executable works without Graphviz shared libraries/plugins in the solver image.
2. The agent contract and the evaluator agree on supported flags, I/O, error handling, assets, build behavior, and time limits.
3. Every scored feature maps to a documented capability and an explicit comparator assertion. No hidden flag or dependency surprise.
4. Reference self-replay is perfect and deterministic. No-op, topology-only, and oracle-assisted straight-edge baselines reveal the expected gradient.
5. Image/source/golden leakage and malicious-candidate probes all fail.
6. Run independent frontier attempts and publish the measured distribution in `validation/README.md`.
