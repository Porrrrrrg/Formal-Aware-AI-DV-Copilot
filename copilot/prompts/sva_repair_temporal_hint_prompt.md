# Temporal-Hint SVA Repair Prompt

Repair exactly one SystemVerilog Assertion using the supplied intent, broken SVA, allowed signals, and clock/reset semantics.

This variant emphasizes temporal operators, antecedent/consequent placement, reset polarity, and handshake cycle boundaries. It intentionally does not expose full counterexample summaries beyond the tool feedback string.

Rules:

1. Preserve the supplied `property_id`.
2. Use only identifiers listed in `allowed_signal_whitelist` plus SystemVerilog/SVA built-ins such as `$past` and `$stable`.
3. Align the assertion clock and reset with `reset_clock_semantics`.
4. Check whether the repair needs same-cycle implication (`|->`), next-cycle implication (`|=>`), `$past`, or a missing antecedent guard.
5. Do not strengthen the property in a way that hides a design or assumption bug.

Return valid JSON matching `sva_repair_candidate.schema.json` with `property_id`, `sva`, and `explanation`.
