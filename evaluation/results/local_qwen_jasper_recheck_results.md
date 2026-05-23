# Local Qwen JasperGold Re-check Results

Date: 2026-05-23T08:34:05Z

Host: `moore.wot.ece.northwestern.edu`

JasperGold executable: `/vol/cadence2018/XCELIUM1809/tools.lnx86/jasper/bin/jg`

Resolved executable: `/vol/cadence2018/XCELIUM1809/tools.lnx86/jasper/bin/jg`

Source checkpoint: `v1.1.2-local-qwen-full-benchmark`

Raw Qwen artifact: `artifacts/qwen_jasper_recheck/sva_repair_qwen_full.json`

This is a JasperGold-backed re-check of saved local Qwen SVA repair outputs. It is not Codex CLI performance, not official FVEval performance, and not production signoff.

Proof outcomes are scoped to the generated harnesses, assumptions, properties, and JasperGold environment used for this run. A proof pass does not establish full semantic intent equivalence.

## Summary

| Metric | Value |
| --- | ---: |
| Candidates rechecked | 23 |
| Syntax pass rate | 0.957 |
| Proven count | 22 |
| Falsified count | 0 |
| Undetermined count | 0 |
| Vacuous count | 0 |
| Not flagged vacuous count | 23 |
| Exact-match success but JasperGold failed | 0 |
| Proof passed but exact match failed | 1 |
| Hallucinated signal caused syntax failure | 1 |

Proof status counts:

```json
{
  "not_reported": 1,
  "proven": 22
}
```

Vacuity status counts:

```json
{
  "not_reported": 23
}
```

## Exact-Match Success But JasperGold Failed

None.

## Proof Passed But Exact Match Failed

| Case | Design | Qwen exact | Syntax | Proof | Vacuity | Report |
| --- | --- | ---: | ---: | --- | --- | --- |
| `repair_arbiter_single_req1_wrong_grant` | `arbiter_rr2` | false | true | `proven` | `not_reported` | `jasper/reports/qwen_jasper_recheck/local_qwen_sva_repair_full/repair_arbiter_single_req1_wrong_grant` |

## Hallucinated Signal Syntax Failures

| Case | Design | Qwen exact | Syntax | Proof | Vacuity | Report |
| --- | --- | ---: | ---: | --- | --- | --- |
| `repair_fifo_reset_wrong_polarity` | `fifo_1r1w` | false | false | `not_reported` | `not_reported` | `jasper/reports/qwen_jasper_recheck/local_qwen_sva_repair_full/repair_fifo_reset_wrong_polarity` |

## All Rechecked Candidates

| Case | Design | Qwen exact | Syntax | Proof | Vacuity | Report |
| --- | --- | ---: | ---: | --- | --- | --- |
| `repair_arbiter_mutex_syntax` | `arbiter_rr2` | true | true | `proven` | `not_reported` | `jasper/reports/qwen_jasper_recheck/local_qwen_sva_repair_full/repair_arbiter_mutex_syntax` |
| `repair_arbiter_spurious_unknown_signal` | `arbiter_rr2` | true | true | `proven` | `not_reported` | `jasper/reports/qwen_jasper_recheck/local_qwen_sva_repair_full/repair_arbiter_spurious_unknown_signal` |
| `repair_arbiter_single_req1_wrong_grant` | `arbiter_rr2` | false | true | `proven` | `not_reported` | `jasper/reports/qwen_jasper_recheck/local_qwen_sva_repair_full/repair_arbiter_single_req1_wrong_grant` |
| `repair_arbiter_turn0_missing_condition` | `arbiter_rr2` | true | true | `proven` | `not_reported` | `jasper/reports/qwen_jasper_recheck/local_qwen_sva_repair_full/repair_arbiter_turn0_missing_condition` |
| `repair_arbiter_reset_wrong_polarity` | `arbiter_rr2` | true | true | `proven` | `not_reported` | `jasper/reports/qwen_jasper_recheck/local_qwen_sva_repair_full/repair_arbiter_reset_wrong_polarity` |
| `repair_arbiter_fairness_too_strong` | `arbiter_rr2` | true | true | `proven` | `not_reported` | `jasper/reports/qwen_jasper_recheck/local_qwen_sva_repair_full/repair_arbiter_fairness_too_strong` |
| `repair_buffer_reset_syntax` | `rv_buffer` | true | true | `proven` | `not_reported` | `jasper/reports/qwen_jasper_recheck/local_qwen_sva_repair_full/repair_buffer_reset_syntax` |
| `repair_buffer_unknown_data_signal` | `rv_buffer` | true | true | `proven` | `not_reported` | `jasper/reports/qwen_jasper_recheck/local_qwen_sva_repair_full/repair_buffer_unknown_data_signal` |
| `repair_buffer_capture_missing_fire` | `rv_buffer` | true | true | `proven` | `not_reported` | `jasper/reports/qwen_jasper_recheck/local_qwen_sva_repair_full/repair_buffer_capture_missing_fire` |
| `repair_buffer_full_clear_wrong_guard` | `rv_buffer` | true | true | `proven` | `not_reported` | `jasper/reports/qwen_jasper_recheck/local_qwen_sva_repair_full/repair_buffer_full_clear_wrong_guard` |
| `repair_buffer_simul_unknown_signal` | `rv_buffer` | true | true | `proven` | `not_reported` | `jasper/reports/qwen_jasper_recheck/local_qwen_sva_repair_full/repair_buffer_simul_unknown_signal` |
| `repair_buffer_out_valid_wrong_relation` | `rv_buffer` | true | true | `proven` | `not_reported` | `jasper/reports/qwen_jasper_recheck/local_qwen_sva_repair_full/repair_buffer_out_valid_wrong_relation` |
| `repair_apb_setup_syntax` | `apb_regblock` | true | true | `proven` | `not_reported` | `jasper/reports/qwen_jasper_recheck/local_qwen_sva_repair_full/repair_apb_setup_syntax` |
| `repair_apb_write_wrong_addr` | `apb_regblock` | true | true | `proven` | `not_reported` | `jasper/reports/qwen_jasper_recheck/local_qwen_sva_repair_full/repair_apb_write_wrong_addr` |
| `repair_apb_read_unknown_signal` | `apb_regblock` | true | true | `proven` | `not_reported` | `jasper/reports/qwen_jasper_recheck/local_qwen_sva_repair_full/repair_apb_read_unknown_signal` |
| `repair_apb_pready_missing_access` | `apb_regblock` | true | true | `proven` | `not_reported` | `jasper/reports/qwen_jasper_recheck/local_qwen_sva_repair_full/repair_apb_pready_missing_access` |
| `repair_apb_reset_wrong_polarity` | `apb_regblock` | true | true | `proven` | `not_reported` | `jasper/reports/qwen_jasper_recheck/local_qwen_sva_repair_full/repair_apb_reset_wrong_polarity` |
| `repair_apb_invalid_missing_inside` | `apb_regblock` | true | true | `proven` | `not_reported` | `jasper/reports/qwen_jasper_recheck/local_qwen_sva_repair_full/repair_apb_invalid_missing_inside` |
| `repair_fifo_no_underflow_wrong_guard` | `fifo_1r1w` | true | true | `proven` | `not_reported` | `jasper/reports/qwen_jasper_recheck/local_qwen_sva_repair_full/repair_fifo_no_underflow_wrong_guard` |
| `repair_fifo_overflow_missing_pop_exception` | `fifo_1r1w` | true | true | `proven` | `not_reported` | `jasper/reports/qwen_jasper_recheck/local_qwen_sva_repair_full/repair_fifo_overflow_missing_pop_exception` |
| `repair_fifo_pop_data_unknown_signal` | `fifo_1r1w` | true | true | `proven` | `not_reported` | `jasper/reports/qwen_jasper_recheck/local_qwen_sva_repair_full/repair_fifo_pop_data_unknown_signal` |
| `repair_fifo_reset_wrong_polarity` | `fifo_1r1w` | false | false | `not_reported` | `not_reported` | `jasper/reports/qwen_jasper_recheck/local_qwen_sva_repair_full/repair_fifo_reset_wrong_polarity` |
| `repair_fifo_eventual_pop_too_fast` | `fifo_1r1w` | true | true | `proven` | `not_reported` | `jasper/reports/qwen_jasper_recheck/local_qwen_sva_repair_full/repair_fifo_eventual_pop_too_fast` |
