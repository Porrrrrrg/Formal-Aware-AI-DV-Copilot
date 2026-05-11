# Counterexample-Aware SVA Repair Prompt

You are repairing exactly one SystemVerilog Assertion using JasperGold feedback and local scaffold evidence.

Use only the supplied context. Do not invent signals, parameters, clocks, resets, helper functions, or properties. If a field is null, empty, or absent, treat it as unavailable and do not infer hidden evidence. If the property is correct and the RTL or assumptions are wrong, say so in the explanation rather than masking the design or constraint issue.

When playbook guidance is available, consult `copilot/playbooks/cex_debug_playbook.md#cex-review-checklist`, `copilot/playbooks/assumption_vacuity_playbook.md#review-flow`, and `copilot/playbooks/formal_review_checklist.md#checklist` for review focus only; do not copy playbook prose into the response.

The repair context explicitly separates:

- `failing_property_intent`: intended behavior for the failing property.
- `broken_sva`: the current failing assertion to repair.
- `jasper_status`: JasperGold syntax/proof/vacuity status when available.
- `failing_cycle`: counterexample failure cycle when available.
- `expected_behavior`: behavior the property should allow or require.
- `observed_behavior`: behavior seen in the counterexample or failure summary.
- `relevant_signal_values`: signal values, events, or trace snippets relevant to the failure.
- `allowed_signal_whitelist`: the complete signal/property identifier whitelist for the candidate SVA.
- `reset_clock_semantics`: clock, reset, and reset-polarity evidence from the case and failing SVA.
- `assumption_risks`: active assumption or constraint risks that may explain overconstraint or vacuity.
- `vacuity_hint`: vacuity status or hint when available.

Repair rules:

1. Preserve the property id unless the context explicitly says it is wrong.
2. Use only identifiers from `allowed_signal_whitelist` plus SystemVerilog/SVA built-ins such as `$past` and `$stable`.
3. For syntax-only failures, make the smallest edit that restores valid SVA syntax before changing semantics.
4. For overbroad properties, add the missing antecedent guard named by the intent, protocol semantics, or counterexample evidence.
5. For reset failures, align the assertion with `reset_clock_semantics`; do not add or remove `disable iff` unless the evidence requires it.
6. For counterexample failures, reconcile `expected_behavior` with `observed_behavior` at `failing_cycle` using `relevant_signal_values`.
7. For vacuity or assumption-risk evidence, do not strengthen the property in a way that hides overconstraint.

Return valid JSON matching `sva_repair_output.schema.json` with `property_id`, `sva`, and `explanation`.
