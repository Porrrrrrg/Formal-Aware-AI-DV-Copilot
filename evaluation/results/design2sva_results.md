# Design2SVA Results

These results are generated from the retrieval-assisted Design2SVA scaffold. Rows are separated by artifact and provenance so deterministic scaffold, replay, real LLM, and JasperGold-checked runs are not conflated.

## Summary

| Artifact | Mode | Cases | k | syntax@1 | syntax@k | proven@1 | proven@k | non_vacuous@k | hallucinated_signal_rate | fallback_rate | valid_json_rate | avg_rounds | repair_success | Source | Formal | Root-cause candidates |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | --- |
| design2sva_eval_local.json | deterministic_scaffold | 3 | 3 | 1.000 | 1.000 | 0.000 | 0.000 | 0.000 | 0.000 | 1.000 | 1.000 | 0.000 | 0.000 | structured_fallback=9 | not_run | unknown |
| design2sva_eval_replay_local.json | replay | 3 | 3 | 1.000 | 1.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 1.000 | 0.000 | 0.000 | replay=9 | not_run | unknown |
| design2sva_eval_codex_subset.json | real_llm | 3 | 3 | 1.000 | 1.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 1.000 | 1.000 | 1.000 | llm=9 | not_run | unknown |
| design2sva_eval_codex_jasper_subset.json | real_llm | 3 | 3 | 1.000 | 1.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 1.000 | 1.000 | 0.000 | llm=9 | measured | unknown |
| design2sva_eval_anti_vacuity_jasper_subset.json | replay | 3 | 3 | 1.000 | 1.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 1.000 | 1.000 | 0.000 | llm=9 | measured | unknown |
| design2sva_eval_anti_vacuity_replay.json | replay | 1 | 1 | 1.000 | 1.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 1.000 | 1.000 | 1.000 | replay=1 | replayed | unknown |
| design2sva_eval_antivacuity_codex_fixed_wrapper_rerun.json | committed_codex_candidate_replay | 3 | 5 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.000 | 0.000 | 1.000 | 0.000 | 0.000 | llm=15 | measured | unknown=15 |
| design2sva_eval_antivacuity_codex_new_jasper_subset.json | replay | 3 | 5 | 1.000 | 1.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 1.000 | 1.000 | 0.000 | llm=15 | measured | unknown |
| design2sva_eval_antivacuity_codex_new_subset.json | real_llm | 3 | 5 | 1.000 | 1.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 1.000 | 1.000 | 1.000 | llm=15 | not_run | unknown |
| design2sva_eval_codex_fixed_wrapper_rerun.json | committed_codex_candidate_replay | 3 | 3 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.000 | 0.000 | 1.000 | 0.000 | 0.000 | llm=9 | measured | unknown=9 |
| design2sva_eval_reference_oracle_fixed_wrapper_sanity.json | reference_oracle_fixed_wrapper_sanity | 3 | 1 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.000 | 0.000 | 1.000 | 0.000 | 0.000 | reference_oracle=3 | measured | unknown=3 |
| design2sva_eval_reference_oracle_jasper.json | reference_oracle | 3 | 1 | 1.000 | 1.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 1.000 | 0.000 | 0.000 | reference_oracle=3 | measured | unknown |
| design2sva_eval_reference_oracle_local.json | reference_oracle | 3 | 1 | 1.000 | 1.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 1.000 | 0.000 | 0.000 | reference_oracle=3 | not_run | unknown=3 |
| design2sva_eval_reference_oracle_parity_jasper.json | reference_oracle | 3 | 1 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.000 | 0.000 | 1.000 | 0.000 | 0.000 | reference_oracle=3 | measured | unknown=3 |
| design2sva_eval_reference_oracle_parity_local.json | reference_oracle | 3 | 1 | 1.000 | 1.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 1.000 | 0.000 | 0.000 | reference_oracle=3 | not_run | unknown=3 |
| design2sva_eval_reference_oracle_rootcause_jasper.json | reference_oracle | 3 | 1 | 1.000 | 1.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 1.000 | 0.000 | 0.000 | reference_oracle=3 | measured | design2sva_embedding_bug=3 |

## Provenance

### design2sva_eval_local.json

- Mode: `deterministic_scaffold`
- Source counts: structured_fallback=9
- Failure categories: passed=9
- Root-cause candidates: unknown
- Formal metrics status: `not_run`

### design2sva_eval_replay_local.json

- Mode: `replay`
- Source counts: replay=9
- Failure categories: passed=9
- Root-cause candidates: unknown
- Formal metrics status: `not_run`

### design2sva_eval_codex_subset.json

- Mode: `real_llm`
- Source counts: llm=9
- Failure categories: passed=9, temporal_mismatch=9
- Root-cause candidates: unknown
- Formal metrics status: `not_run`

### design2sva_eval_codex_jasper_subset.json

- Mode: `real_llm`
- Source counts: llm=9
- Failure categories: weak_vacuous_assertion=18
- Root-cause candidates: unknown
- Formal metrics status: `measured`

### design2sva_eval_anti_vacuity_jasper_subset.json

- Mode: `replay`
- Source counts: llm=9
- Failure categories: unreachable_antecedent=12, unreachable_cover_goal=6
- Root-cause candidates: unknown
- Formal metrics status: `measured`

### design2sva_eval_anti_vacuity_replay.json

- Mode: `replay`
- Source counts: replay=1
- Failure categories: proven_non_vacuous=1, unreachable_antecedent=1
- Root-cause candidates: unknown
- Formal metrics status: `replayed`

### design2sva_eval_antivacuity_codex_fixed_wrapper_rerun.json

- Mode: `committed_codex_candidate_replay`
- Source counts: llm=15
- Failure categories: proven_non_vacuous=15
- Root-cause candidates: unknown=15
- Formal metrics status: `measured`

### design2sva_eval_antivacuity_codex_new_jasper_subset.json

- Mode: `replay`
- Source counts: llm=15
- Failure categories: unreachable_antecedent=20, unreachable_cover_goal=10
- Root-cause candidates: unknown
- Formal metrics status: `measured`

### design2sva_eval_antivacuity_codex_new_subset.json

- Mode: `real_llm`
- Source counts: llm=15
- Failure categories: not_run=15, temporal_mismatch=15
- Root-cause candidates: unknown
- Formal metrics status: `not_run`

### design2sva_eval_codex_fixed_wrapper_rerun.json

- Mode: `committed_codex_candidate_replay`
- Source counts: llm=9
- Failure categories: proven_non_vacuous=9
- Root-cause candidates: unknown=9
- Formal metrics status: `measured`

### design2sva_eval_reference_oracle_fixed_wrapper_sanity.json

- Mode: `reference_oracle_fixed_wrapper_sanity`
- Source counts: reference_oracle=3
- Failure categories: proven_non_vacuous=3
- Root-cause candidates: unknown=3
- Formal metrics status: `measured`

### design2sva_eval_reference_oracle_jasper.json

- Mode: `reference_oracle`
- Source counts: reference_oracle=3
- Failure categories: unreachable_antecedent=2, unreachable_cover_goal=1
- Root-cause candidates: unknown
- Formal metrics status: `measured`

### design2sva_eval_reference_oracle_local.json

- Mode: `reference_oracle`
- Source counts: reference_oracle=3
- Failure categories: not_run=3
- Root-cause candidates: unknown=3
- Formal metrics status: `not_run`

### design2sva_eval_reference_oracle_parity_jasper.json

- Mode: `reference_oracle`
- Source counts: reference_oracle=3
- Failure categories: proven_non_vacuous=3
- Root-cause candidates: unknown=3
- Formal metrics status: `measured`

### design2sva_eval_reference_oracle_parity_local.json

- Mode: `reference_oracle`
- Source counts: reference_oracle=3
- Failure categories: not_run=3
- Root-cause candidates: unknown=3
- Formal metrics status: `not_run`

### design2sva_eval_reference_oracle_rootcause_jasper.json

- Mode: `reference_oracle`
- Source counts: reference_oracle=3
- Failure categories: unreachable_antecedent=2, unreachable_cover_goal=1
- Root-cause candidates: design2sva_embedding_bug=3
- Formal metrics status: `measured`

## Claim Boundary

- Dry-run, replay, and deterministic scaffold rows do not measure hosted model quality.
- Real LLM rows measure schema-constrained hosted-model behavior only when `source_counts` records `llm` outputs and fallback is low.
- `proven@*` and `non_vacuous@k` are only meaningful when real JasperGold checks are enabled and available.
- Exact/reference agreement on local fixtures is a scaffold signal, not functional equivalence or production signoff.
