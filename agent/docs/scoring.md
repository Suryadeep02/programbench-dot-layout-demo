# Local scoring contract

> Historical calibration contract: these inputs were held out during the recorded attempts. The corpus in this public demo is now public.

Each valid hidden DOT file is one equally weighted case. The evaluator requires exit code zero and a well-formed complete plain stream. It compares graph scale and dimensions, the full node set and node fields, and the full edge multiset including endpoint/port, ordered spline control points, optional label and label center, style, and color. Missing or extra records, duplicate nodes, wrong control-point counts, malformed numbers, NaN/Infinity, and extra text fail the case.

Numeric fields are compared in inches. Every numeric value must be within 0.03 of the reference, and the mean absolute difference over all geometric values in a case must be at most 0.01. The `n` control-point count is exact. Record order and insignificant whitespace are ignored. Quoted and unquoted tokens that decode to the same value are equivalent. Parallel edges are matched one to one; a candidate cannot reuse one edge record to satisfy multiple reference edges. There is no translation, rotation, scaling, or path-shape normalization.

Reference results are generated and replayed in the same pinned runtime family used for candidate grading. Hidden inputs are valid DOT, so diagnostic wording for invalid input is outside the score. Successful runs may write diagnostics to standard error, but only standard output is parsed.
