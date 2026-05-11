# FVEval Subset Results

## Summary

Source: [https://github.com/NVlabs/FVEval](https://github.com/NVlabs/FVEval) at `141afe7dcf03a0b86547b94657d9d610b6087724`.

- Design2SVA: 10
- NL2SVA-Human: 10
- NL2SVA-Machine: 10

| Metric | Value |
| --- | ---: |
| Cases | 30 |
| Syntax pass | 1.000 |
| Exact/reference match | 0.000 |
| Exact/reference eligible cases | 20 |
| Valid JSON | 1.000 |
| Fallback | 1.000 |
| Hallucinated signal rate | 0.000 |
| Invalid prediction JSON rows | 0 |

## Metrics By Subset

| Subset | Cases | Syntax | Exact/reference | Exact eligible | Valid JSON | Fallback | Hallucinated signals | Jasper |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| Design2SVA | 10 | 1.000 | n/a | 0 | 1.000 | 1.000 | 0.000 | not_run |
| NL2SVA-Human | 10 | 1.000 | 0.000 | 10 | 1.000 | 1.000 | 0.000 | not_run |
| NL2SVA-Machine | 10 | 1.000 | 0.000 | 10 | 1.000 | 1.000 | 0.000 | not_run |

## Evidence Fields

- Source benchmark: FVEval-compatible subset.
- Case count: 30.
- External reference retained as evaluation metadata only.
- Reference answers omitted from prompt payloads.
- No JasperGold, Codex, or Qwen execution is performed by this runner.

## Case Rows

| Case | Subset | Syntax | Exact | JSON | Fallback | Hallucinated | Jasper |
| --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| fveval_nl2sva_human_00_counter_0 | NL2SVA-Human | True | False | True | True | False | not_run |
| fveval_nl2sva_human_01_counter_1 | NL2SVA-Human | True | False | True | True | False | not_run |
| fveval_nl2sva_human_02_counter_2 | NL2SVA-Human | True | False | True | True | False | not_run |
| fveval_nl2sva_human_03_counter_3 | NL2SVA-Human | True | False | True | True | False | not_run |
| fveval_nl2sva_human_04_counter_4 | NL2SVA-Human | True | False | True | True | False | not_run |
| fveval_nl2sva_human_05_arbiter_0 | NL2SVA-Human | True | False | True | True | False | not_run |
| fveval_nl2sva_human_06_arbiter_3 | NL2SVA-Human | True | False | True | True | False | not_run |
| fveval_nl2sva_human_07_arbiter_4 | NL2SVA-Human | True | False | True | True | False | not_run |
| fveval_nl2sva_human_08_arbiter_5 | NL2SVA-Human | True | False | True | True | False | not_run |
| fveval_nl2sva_human_09_arbiter_6 | NL2SVA-Human | True | False | True | True | False | not_run |
| fveval_nl2sva_machine_00_3_0_0 | NL2SVA-Machine | True | False | True | True | False | not_run |
| fveval_nl2sva_machine_01_3_1_0 | NL2SVA-Machine | True | False | True | True | False | not_run |
| fveval_nl2sva_machine_02_3_2_0 | NL2SVA-Machine | True | False | True | True | False | not_run |
| fveval_nl2sva_machine_03_3_3_0 | NL2SVA-Machine | True | False | True | True | False | not_run |
| fveval_nl2sva_machine_04_3_4_0 | NL2SVA-Machine | True | False | True | True | False | not_run |
| fveval_nl2sva_machine_05_3_5_0 | NL2SVA-Machine | True | False | True | True | False | not_run |
| fveval_nl2sva_machine_06_3_6_0 | NL2SVA-Machine | True | False | True | True | False | not_run |
| fveval_nl2sva_machine_07_3_7_0 | NL2SVA-Machine | True | False | True | True | False | not_run |
| fveval_nl2sva_machine_08_3_8_0 | NL2SVA-Machine | True | False | True | True | False | not_run |
| fveval_nl2sva_machine_09_3_9_0 | NL2SVA-Machine | True | False | True | True | False | not_run |
| fveval_design2sva_pipeline_00_ns_2-w_128-opd_2-0 | Design2SVA | True | n/a | True | True | False | not_run |
| fveval_design2sva_pipeline_01_ns_2-w_128-opd_2-1 | Design2SVA | True | n/a | True | True | False | not_run |
| fveval_design2sva_pipeline_02_ns_2-w_128-opd_2-2 | Design2SVA | True | n/a | True | True | False | not_run |
| fveval_design2sva_pipeline_03_ns_2-w_128-opd_2-3 | Design2SVA | True | n/a | True | True | False | not_run |
| fveval_design2sva_pipeline_04_ns_2-w_128-opd_2-4 | Design2SVA | True | n/a | True | True | False | not_run |
| fveval_design2sva_fsm_00_ni_4_nn_4_ne_4_wd_32_opd_2_0 | Design2SVA | True | n/a | True | True | False | not_run |
| fveval_design2sva_fsm_01_ni_4_nn_4_ne_4_wd_32_opd_3_0 | Design2SVA | True | n/a | True | True | False | not_run |
| fveval_design2sva_fsm_02_ni_4_nn_4_ne_4_wd_32_opd_4_0 | Design2SVA | True | n/a | True | True | False | not_run |
| fveval_design2sva_fsm_03_ni_4_nn_4_ne_4_wd_32_opd_5_0 | Design2SVA | True | n/a | True | True | False | not_run |
| fveval_design2sva_fsm_04_ni_4_nn_4_ne_8_wd_32_opd_2_0 | Design2SVA | True | n/a | True | True | False | not_run |

## Limitations

- This local subset runner is not apples-to-apples with FVEval official results.
- This local subset runner does not reproduce FVEval's commercial functional-equivalence flow.
- Design2SVA exact/reference match is not treated as functional equivalence.
- Jasper proof is reported as `not_run` unless a future local harness integration is added and explicitly enabled.
