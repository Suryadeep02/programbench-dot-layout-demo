# Public export boundaries

This is a separate public application/demo snapshot. The original repository and history remain unchanged.

Preserved: task, fixture generator, comparator, scoring rules, all 120 input/golden pairs, source checks, isolation recipe and tests. The runner's file write uses an explicit LF text handle for compatibility; scoring semantics are unchanged.

Derived: eight recorded result files retain trial label, model/effort, time ceiling, historical code hashes, score and per-case decisions. These are historical observations, not fresh attempts.

Omitted: old Git history and contact metadata; raw trajectories and session identifiers; token telemetry and run timestamps; candidate workspaces; compiled references and binaries; upstream source archive; machine-specific image identifiers; private review correspondence. The omission of candidate sources means this public export alone cannot replay the eight historical submissions.

The corpus is now public. It is an inspectable demonstration of evaluator design, not a secret held-out benchmark. Runtime guards still restrict what a candidate container receives during a run, but cannot undo public corpus disclosure.

No confidential employer/client materials or unrelated project details are included. Do not infer production delivery or ownership of an LLM reinforcement-learning pipeline from this demo.
