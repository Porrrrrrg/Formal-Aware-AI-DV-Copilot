# Design2SVA Stage 17 Ablation Summary

This table is built from existing committed artifacts only. It sends no new external LLM prompts and does not invoke JasperGold.

## Summary

| Row | Status | Artifact | Cases | k | valid_json_rate | fallback_rate | hallucinated_signal_rate | syntax@1 | syntax@k | proven@1 | proven@k | non_vacuous@k | proven_non_vacuous@k | antecedent_reachable@k | wrapper_parity_pass_rate | average_rounds | source_counts | formal_metrics_status |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |
| `reference_oracle` | `measured` | `design2sva_reference_oracle_expanded_jasper.json` | 12 | 1 | 1.000 | 0.000 | 0.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.000 | reference_oracle=12 | measured |
| `native_oracle` | `measured` | `design2sva_native_oracle_expanded_jasper.json` | 12 | 1 | not_applicable | not_applicable | not_applicable | not_applicable | not_applicable | 1.000 | 1.000 | not_run | not_run | not_applicable | not_applicable | not_applicable | native_reference_oracle=12 | measured |
| `codex_design2sva_current` | `measured` | `design2sva_eval_codex_expanded_jasper.json` | 12 | 3 | 1.000 | 0.000 | 0.000 | 1.000 | 1.000 | 0.750 | 1.000 | 1.000 | 1.000 | 1.000 | 0.000 | 0.194 | llm=36 | replayed |
| `codex_fixed_wrapper_rerun` | `measured` | `design2sva_eval_codex_fixed_wrapper_rerun.json` | 3 | 3 | 1.000 | 0.000 | 0.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.000 | 0.000 | llm=9 | measured |
| `codex_antivacuity_current` | `measured` | `design2sva_eval_antivacuity_codex_fixed_wrapper_rerun.json` | 3 | 5 | 1.000 | 0.000 | 0.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.000 | 0.000 | llm=15 | measured |
| `deterministic_scaffold` | `local_only_formal_not_run` | `design2sva_eval_local.json` | 3 | 3 | 1.000 | 1.000 | 0.000 | 1.000 | 1.000 | not_run | not_run | not_run | not_run | not_run | not_run | 0.000 | structured_fallback=9 | not_run |
| `replay_baseline` | `local_only_formal_not_run` | `design2sva_codex_replay_expanded_local.json` | 3 | 3 | 1.000 | 0.000 | 0.000 | 1.000 | 1.000 | not_run | not_run | not_run | not_run | not_run | not_run | 1.000 | llm=9 | not_run |
| `direct_prompt_placeholder` | `not_run` | `not_run` | not_run | not_run | not_run | not_run | not_run | not_run | not_run | not_run | not_run | not_run | not_run | not_run | not_run | not_run | not_run | not_run |
| `no_retrieval_placeholder` | `not_run` | `not_run` | not_run | not_run | not_run | not_run | not_run | not_run | not_run | not_run | not_run | not_run | not_run | not_run | not_run | not_run | not_run | not_run |
| `no_antivacuity_placeholder` | `not_run` | `not_run` | not_run | not_run | not_run | not_run | not_run | not_run | not_run | not_run | not_run | not_run | not_run | not_run | not_run | not_run | not_run | not_run |

## Row Notes

- `reference_oracle`: Expanded fixture reference SVA evaluated through the repaired wrapper.
- `native_oracle`: Expanded fixture reference properties evaluated through native benchmark flows.
- `codex_design2sva_current`: Stage 16 real Codex k=3 candidates replayed with JasperGold evidence.
- `codex_fixed_wrapper_rerun`: Stage 13 committed Codex candidates rerun through the fixed wrapper.
- `codex_antivacuity_current`: Committed anti-vacuity Codex subset after the fixed-wrapper rerun; kept separate from the earlier pre-wrapper anti-vacuity failures.
- `deterministic_scaffold`: Deterministic local scaffold row; no formal backend measurement.
- `replay_baseline`: Stage 14 committed Codex replay baseline without JasperGold measurement.
- `direct_prompt_placeholder`: Direct prompt ablation row reserved for a gated future external LLM run.
  Gated command, not run by this artifact: `python scripts/run_codex_llm_eval.py --task design2sva --k 3 --context-budget 0 --acknowledge-external-send --out evaluation/results/design2sva_direct_prompt.json`
- `no_retrieval_placeholder`: No-retrieval ablation row reserved for a gated future external LLM run.
  Gated command, not run by this artifact: `python scripts/run_codex_llm_eval.py --task design2sva --k 3 --context-budget 0 --acknowledge-external-send --out evaluation/results/design2sva_no_retrieval.json`
- `no_antivacuity_placeholder`: No anti-vacuity repair ablation row reserved for a gated future LLM run.
  Gated command, not run by this artifact: `python scripts/run_codex_llm_eval.py --task design2sva --k 3 --max-repair-rounds 0 --acknowledge-external-send --out evaluation/results/design2sva_no_antivacuity.json`

## Caveats

- Local benchmark only.
- Small N: 12-case expanded Design2SVA benchmark plus smaller legacy controls.
- No production signoff.
- Not an official FVEval reproduction.
- Rows with formal_metrics_status=not_run must not be read as zero proof success.
