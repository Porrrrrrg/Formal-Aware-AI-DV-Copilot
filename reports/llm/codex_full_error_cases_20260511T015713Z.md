# Codex Full Benchmark Error Cases

Run UTC: 2026-05-11T01:57:13Z
Benchmark input SHA: `dec371bd7d4eb9aacf80a28ffc300914a7b45540`

This diagnostic report is sanitized. It includes case identifiers, labels, and aggregate outcomes only. It does not include raw prompts, verbose CLI traces, or Qwen comparisons.

## Summary

| Category | Count |
| --- | ---: |
| SVA repair scaffold misses | 7 |
| Triage label/action misses | 2 |
| Coverage misses | 0 |
| LLM errors | 0 |
| Deterministic fallbacks | 0 |
| Schema drift cases | 0 |

## SVA Repair Scaffold Misses

These cases were attempted with Codex LLM repair outputs but did not reach final scaffold success or final exact match.

| Case ID | Design | Bug Type | Round 0 Status | Final Status | Final Exact Match | Final Hallucinated Signal |
| --- | --- | --- | --- | --- | --- | --- |
| `repair_arbiter_single_req1_wrong_grant` | `arbiter_rr2` | `temporal_or_semantic_error` | `scaffold_fail` | `scaffold_fail` | false | false |
| `repair_arbiter_turn0_missing_condition` | `arbiter_rr2` | `overbroad_property` | `scaffold_fail` | `scaffold_fail` | false | false |
| `repair_buffer_reset_syntax` | `rv_buffer` | `syntax_error` | `syntax_fail` | `scaffold_fail` | false | false |
| `repair_buffer_capture_missing_fire` | `rv_buffer` | `overbroad_property` | `scaffold_fail` | `scaffold_fail` | false | false |
| `repair_apb_setup_syntax` | `apb_regblock` | `syntax_error` | `syntax_fail` | `scaffold_fail` | false | false |
| `repair_apb_pready_missing_access` | `apb_regblock` | `overbroad_property` | `scaffold_fail` | `scaffold_fail` | false | false |
| `repair_apb_reset_wrong_polarity` | `apb_regblock` | `reset_error` | `scaffold_fail` | `scaffold_fail` | false | false |

## Triage Label And Action Misses

These cases produced valid Codex JSON, but the predicted issue type and next action did not match the benchmark labels.

| Case ID | Design | Gold Issue | Predicted Issue | Gold Action | Predicted Action |
| --- | --- | --- | --- | --- | --- |
| `arbiter_A8` | `arbiter_rr2` | `testbench_stimulus_bug` | `reachable_coverage_gap` | `fix_testbench_or_stimulus` | `add_directed_test_or_sequence` |
| `rv_B8` | `rv_buffer` | `testbench_stimulus_bug` | `reachable_coverage_gap` | `fix_testbench_or_stimulus` | `add_directed_test_or_sequence` |

## Coverage Misses

No coverage gap/action misses were observed in the full pass.

## Schema And Fallback Diagnostics

- Schema drift count: 0
- LLM error count: 0
- Fallback count: 0
- Full-pass source counts: `llm`: 71

