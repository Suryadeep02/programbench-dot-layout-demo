# Validation and recorded evidence

## Historical calibration records

These records are derived from saved model runs. They were not generated again for this public release. Raw trajectories and candidate workspaces are deliberately omitted. The public export therefore lets you inspect score arithmetic and per-case decisions, but cannot alone reproduce those model submissions.

| Trial | Recorded model | Effort | Passed | Score |
| --- | --- | --- | --- | --- |
| trial-10 | gpt-6.1-sol | high | 34/120 | 28.33% |
| trial-12 | gpt-5.6-terra | xhigh | 14/120 | 11.67% |
| trial-13 | gpt-6.1-sol | high | 32/120 | 26.67% |
| trial-14 | gpt-5.6-terra | xhigh | 26/120 | 21.67% |
| trial-15 | gpt-6.1-sol | high | 44/120 | 36.67% |
| trial-16 | gpt-5.6-terra | xhigh | 27/120 | 22.50% |
| trial-17 | gpt-6.1-sol | high | 34/120 | 28.33% |
| trial-18 | gpt-5.6-terra | xhigh | 20/120 | 16.67% |

Mean: **24.0625%**. The records contain 960 case decisions in total. The six-hour setting was an upper budget. No general model-ranking or future difficulty conclusion follows from these eight attempts.

## Checks rerun for the public release

Source-only suite: 43 discovered tests, 38 passed and five optional Docker tests skipped in the initial local check. The explicit-LF file write was corrected for Python compatibility after the original test exposed the problem. The comparator, case inputs, goldens, tolerances and score aggregation remain unchanged.

The same source-only suite also passed in the pinned Linux/amd64 GCC image: 38 passed, five optional integration tests skipped. A fresh Docker replay of the existing pinned reference passed 120/120. One existing saved candidate, trial-15, was rebuilt offline and scored 44/120; all 120 pass/fail decisions matched its historical record. The other seven saved candidates were not replayed, and four optional clean-room integration tests were not rerun. The reference was not rebuilt from upstream source in this pass. Details are in [release-checks.json](release-checks.json). No new paid model calibration was run.

## What is still limited

- Publishing this corpus makes it public. It is no longer a secret held-out evaluation set.
- Historical candidate hashes reflect native Windows path ordering. Recomputing on POSIX can differ even for the same mixed-case source tree.
- The original evaluator hash identifies the original recorded setup. The public runner's file-writing compatibility change gives this release a different hash.
- Static source scans and binary similarity heuristics reduce particular shortcut paths; they do not prove a sandbox secure against every malicious submission.
- The public archive excludes candidate workspaces and raw model transcripts. Historical results remain reported observations with internal consistency checks, not independently regenerated model attempts.
