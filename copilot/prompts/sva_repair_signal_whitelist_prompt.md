# Signal-Whitelist SVA Repair Prompt

Repair exactly one SystemVerilog Assertion using only the supplied property intent, broken SVA, and allowed signal whitelist.

This variant intentionally withholds counterexample and temporal-hint emphasis so the ablation can isolate whether a strict signal whitelist alone reduces hallucinated identifiers.

Rules:

1. Use only identifiers listed in `allowed_signal_whitelist` plus SystemVerilog/SVA built-ins such as `$past` and `$stable`.
2. Preserve the supplied `property_id`.
3. Make the smallest repair needed to satisfy the stated property intent.
4. Do not invent helper signals, helper properties, parameters, or functions.
5. If the supplied context is insufficient, return the most conservative syntactically valid repair and explain the uncertainty.

Return valid JSON matching `sva_repair_candidate.schema.json` with `property_id`, `sva`, and `explanation`.
