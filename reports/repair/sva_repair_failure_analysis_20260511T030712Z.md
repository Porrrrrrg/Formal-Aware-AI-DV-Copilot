# Stage 3A SVA Repair Failure Analysis

Created UTC: 2026-05-11T03:07:12Z

## Scope

This report analyzes the 7/18 Codex SVA repair misses reported by the committed Stage 2D sanitized artifacts:

- `reports/llm/codex_full_error_cases_20260511T015713Z.md`
- `reports/llm/codex_full_summary_20260511T015713Z.md`
- `reports/llm/codex_full_manifest_20260511T015713Z.json`
- `benchmarks/sva_repair_cases.json`
- `copilot/prompts/sva_repair_prompt.md`
- `copilot/agents/sva_repair_agent.py`
- `evaluation/run_sva_repair_eval.py`
- `copilot/sva_library.py`

No benchmark was rerun. No raw ignored result artifact was used. The Stage 2D manifest states that the raw full-pass artifacts were not committed, so Codex repaired SVA text is unavailable here. Case-level conclusions below infer only from the committed sanitized status fields and from the broken/reference repair deltas in the source fixture.

## Evaluator Context

The full Codex pass reported 18 SVA repair cases with 11 repair successes. The 7 misses all have:

- `final_status`: `scaffold_fail`
- `final_exact_match`: `false`
- `final_hallucinated_signal`: `false`

In `evaluation/run_sva_repair_eval.py`, `scaffold_fail` without Jasper fields means the candidate passed the lightweight syntax scaffold but did not normalize to the exact reference SVA. Success requires exact normalized match to `reference_sva` and no hallucinated identifiers. Therefore these failures are best read as non-exact scaffold misses, not live Jasper proof failures.

## Case-Level Table

| case_id | design | bug class | original broken SVA | Codex repaired SVA | expected/reference repair | failure type | likely cause | recommended intervention |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `repair_arbiter_single_req1_wrong_grant` | `arbiter_rr2` | `temporal_or_semantic_error` | <code>p_single_req1_grant: assert property (@(posedge clk) disable iff (rst) !req0 && req1 &#124;-> gnt0 && !gnt1);</code> | Unavailable in committed artifacts. Sanitized diagnostics only say final candidate was non-hallucinated and non-exact. | <code>p_single_req1_grant: assert property (@(posedge clk) disable iff (rst) !req0 && req1 &#124;-> !gnt0 && gnt1);</code> | temporal/semantic mismatch | The required repair flips both grant polarities for the single-requester case. A non-exact but syntactically valid final candidate likely failed to preserve the intended requester-to-grant mapping exactly. | Add a requester/grant role checklist to the repair prompt for arbiter properties: identify the active requester, the asserted grant, and the deasserted competing grant before emitting SVA. |
| `repair_arbiter_turn0_missing_condition` | `arbiter_rr2` | `overbroad_property` | <code>p_both_req_priority_turn0: assert property (@(posedge clk) disable iff (rst) req0 && req1 &#124;-> gnt0 && !gnt1);</code> | Unavailable in committed artifacts. Sanitized diagnostics only say final candidate was non-hallucinated and non-exact. | <code>p_both_req_priority_turn0: assert property (@(posedge clk) disable iff (rst) req0 && req1 && !turn &#124;-> gnt0 && !gnt1);</code> | overbroad / weak property | The repair requires adding the missing `!turn` antecedent guard. The prompt includes allowed signals and intent, but no structured guard-completeness requirement. | Add an overbroad-property repair rule: every condition named in the intent must appear in the antecedent unless explicitly explained. |
| `repair_buffer_reset_syntax` | `rv_buffer` | `syntax_error` | <code>p_reset_empty: assert property (@(posedge clk) rst &#124;=> !full && !out_valid</code> | Unavailable in committed artifacts. Sanitized diagnostics show round 0 syntax failure and final non-exact scaffold failure. | <code>p_reset_empty: assert property (@(posedge clk) rst &#124;=> !full && !out_valid);</code> | syntax-only | The fixture repair is a minimal terminator/parenthesis fix. Final `scaffold_fail` indicates Codex moved past syntax but did not emit the exact minimal repair. | Add a syntax-only mode when feedback is local syntax failure: first attempt the smallest edit that balances delimiters and appends the missing semicolon, with no semantic rewrite. |
| `repair_buffer_capture_missing_fire` | `rv_buffer` | `overbroad_property` | <code>p_capture_on_input_fire: assert property (@(posedge clk) disable iff (rst) in_valid &#124;=> full && out_data == $past(in_data));</code> | Unavailable in committed artifacts. Sanitized diagnostics only say final candidate was non-hallucinated and non-exact. | <code>p_capture_on_input_fire: assert property (@(posedge clk) disable iff (rst) in_valid && in_ready &#124;=> full && out_data == $past(in_data));</code> | overbroad / weak property | The broken antecedent uses `in_valid` without the ready/valid fire condition. A syntactically valid non-exact repair likely missed the handshake guard or changed timing/data sampling. | Add a ready/valid handshake invariant to repair prompts: "input fire" means `in_valid && in_ready`; "output fire" means `out_valid && out_ready`. |
| `repair_apb_setup_syntax` | `apb_regblock` | `syntax_error` | <code>p_setup_then_enable: assert property (@(posedge pclk) disable iff (!presetn) psel && !penable &#124;=> psel && penable)</code> | Unavailable in committed artifacts. Sanitized diagnostics show round 0 syntax failure and final non-exact scaffold failure. | <code>p_setup_then_enable: assert property (@(posedge pclk) disable iff (!presetn) psel && !penable &#124;=> psel && penable);</code> | syntax-only | The fixture repair is only the final semicolon. Codex apparently produced a syntactically acceptable but non-reference assertion, which the exact-match scaffold rejected. | Use a minimal syntax repair pass before semantic repair for syntax-error cases; preserve the operator, antecedent, consequent, clock, and reset unless diagnostics name a semantic issue. |
| `repair_apb_pready_missing_access` | `apb_regblock` | `overbroad_property` | <code>p_pready_response_valid: assert property (@(posedge pclk) disable iff (!presetn) psel &#124;-> pready);</code> | Unavailable in committed artifacts. Sanitized diagnostics only say final candidate was non-hallucinated and non-exact. | <code>p_pready_response_valid: assert property (@(posedge pclk) disable iff (!presetn) psel && penable &#124;-> pready);</code> | overbroad / weak property | The missing APB access-phase guard is `penable`. The prompt lacks an explicit APB phase glossary, so `psel` may have been treated as the full transaction condition. | Add protocol glossary snippets to repair context; for APB, define setup as `psel && !penable` and access as `psel && penable`. |
| `repair_apb_reset_wrong_polarity` | `apb_regblock` | `reset_error` | <code>p_reset_clears_registers: assert property (@(posedge pclk) presetn &#124;=> reg0 == 32'h0 && reg1 == 32'h0);</code> | Unavailable in committed artifacts. Sanitized diagnostics only say final candidate was non-hallucinated and non-exact. | <code>p_reset_clears_registers: assert property (@(posedge pclk) !presetn &#124;=> reg0 == 32'h0 && reg1 == 32'h0);</code> | reset semantics | `presetn` is active-low. The repair requires polarity inversion without adding `disable iff` or changing timing. | Add a reset-polarity extraction step to the prompt and candidate review: state whether reset is active-high or active-low, then require the reset antecedent to match that polarity. |

## Classification Summary

| classification | primary count | cases |
| --- | ---: | --- |
| syntax-only | 2 | `repair_buffer_reset_syntax`, `repair_apb_setup_syntax` |
| unknown signal | 0 | None. All 7 had `final_hallucinated_signal=false`. |
| reset semantics | 1 | `repair_apb_reset_wrong_polarity` |
| overbroad / weak property | 3 | `repair_arbiter_turn0_missing_condition`, `repair_buffer_capture_missing_fire`, `repair_apb_pready_missing_access` |
| temporal/semantic mismatch | 1 | `repair_arbiter_single_req1_wrong_grant` |
| vacuity risk | 0 | No committed diagnostics report vacuity. |
| evaluator/scaffold limitation | 7 secondary | All misses are exact-match scaffold misses with raw repaired SVA unavailable; semantic equivalence cannot be audited from committed artifacts. |

## Cross-Case Findings

1. The failures are not identifier hallucination failures. The committed sanitized report marks all 7 final candidates as non-hallucinated.
2. The failures are not demonstrated Jasper proof failures. The Stage 2D full pass did not run live Jasper final proof, and `scaffold_fail` comes from the local exact-match scaffold path.
3. Two syntax cases likely need a minimal-edit syntax repair path. The expected repairs only close the assertion and add `;`, but the final outputs were syntactically valid and non-exact.
4. Three overbroad-property failures all require adding a missing antecedent guard from protocol intent: `!turn`, `in_ready`, or `penable`.
5. The APB reset miss is a polarity-specific failure: `presetn` must be negated in the antecedent.

## Recommended Interventions

1. Add a syntax-first repair mode for `syntax_error` cases that performs the smallest valid SVA edit before attempting semantic changes.
2. Add protocol-specific guard hints to repair prompts for ready/valid, APB setup/access phases, and arbiter turn arbitration.
3. Require candidate explanations to enumerate antecedent guards from the property intent and map them to emitted SVA terms.
4. For reset cases, require an explicit active-high/active-low reset declaration before the candidate SVA.
5. Improve committed diagnostics for future benchmark reports by including sanitized final candidate SVA text or a normalized candidate/reference diff, so Stage 3 analysis can distinguish true semantic failures from exact-match wording differences.

## Limitations

Raw Codex repair outputs were not committed. This report does not claim which final SVA Codex emitted for any failed case and does not claim any new benchmark result. The likely-cause analysis is constrained to the source fixture deltas and the committed sanitized status fields.
