# Design2SVA Results

These results are generated from the retrieval-assisted Design2SVA scaffold. Rows are separated by artifact and provenance so deterministic scaffold, replay, real LLM, and JasperGold-checked runs are not conflated.

## Summary

| Artifact | Mode | Cases | k | syntax@1 | syntax@k | proven@1 | proven@k | non_vacuous@k | hallucinated_signal_rate | fallback_rate | valid_json_rate | avg_rounds | repair_success | Source | Formal |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |
| design2sva_eval_local.json | deterministic_scaffold | 3 | 3 | 1.000 | 1.000 | 0.000 | 0.000 | 0.000 | 0.000 | 1.000 | 1.000 | 0.000 | 0.000 | structured_fallback=9 | not_run |
| design2sva_eval_replay_local.json | replay | 3 | 3 | 1.000 | 1.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 1.000 | 0.000 | 0.000 | replay=9 | not_run |
| design2sva_eval_codex_subset.json | real_llm | 3 | 3 | 1.000 | 1.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 1.000 | 1.000 | 1.000 | llm=9 | not_run |
| design2sva_eval_codex_jasper_subset.json | real_llm | 3 | 3 | 1.000 | 1.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 1.000 | 1.000 | 0.000 | llm=9 | measured |
| design2sva_eval_anti_vacuity_jasper_subset.json | replay | 3 | 3 | 1.000 | 1.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 1.000 | 1.000 | 0.000 | llm=9 | measured |
| design2sva_eval_anti_vacuity_replay.json | replay | 1 | 1 | 1.000 | 1.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 1.000 | 1.000 | 1.000 | replay=1 | replayed |
| design2sva_eval_antivacuity_codex_new_jasper_subset.json | replay | 3 | 5 | 1.000 | 1.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 1.000 | 1.000 | 0.000 | llm=15 | measured |
| design2sva_eval_antivacuity_codex_new_subset.json | real_llm | 3 | 5 | 1.000 | 1.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 1.000 | 1.000 | 1.000 | llm=15 | not_run |

## Provenance

### design2sva_eval_local.json

- Mode: `deterministic_scaffold`
- Source counts: structured_fallback=9
- Failure categories: passed=9
- Formal metrics status: `not_run`

### design2sva_eval_replay_local.json

- Mode: `replay`
- Source counts: replay=9
- Failure categories: passed=9
- Formal metrics status: `not_run`

### design2sva_eval_codex_subset.json

- Mode: `real_llm`
- Source counts: llm=9
- Failure categories: passed=9, temporal_mismatch=9
- Formal metrics status: `not_run`

### design2sva_eval_codex_jasper_subset.json

- Mode: `real_llm`
- Source counts: llm=9
- Failure categories: weak_vacuous_assertion=18
- Formal metrics status: `measured`

### design2sva_eval_anti_vacuity_jasper_subset.json

- Mode: `replay`
- Source counts: llm=9
- Failure categories: unreachable_antecedent=12, unreachable_cover_goal=6
- Formal metrics status: `measured`

### design2sva_eval_anti_vacuity_replay.json

- Mode: `replay`
- Source counts: replay=1
- Failure categories: proven_non_vacuous=1, unreachable_antecedent=1
- Formal metrics status: `replayed`

### design2sva_eval_antivacuity_codex_new_jasper_subset.json

- Mode: `replay`
- Source counts: llm=15
- Failure categories: unreachable_antecedent=20, unreachable_cover_goal=10
- Formal metrics status: `measured`

### design2sva_eval_antivacuity_codex_new_subset.json

- Mode: `real_llm`
- Source counts: llm=15
- Failure categories: not_run=15, temporal_mismatch=15
- Formal metrics status: `not_run`

## Claim Boundary

- Dry-run, replay, and deterministic scaffold rows do not measure hosted model quality.
- Real LLM rows measure schema-constrained hosted-model behavior only when `source_counts` records `llm` outputs and fallback is low.
- `proven@*` and `non_vacuous@k` are only meaningful when real JasperGold checks are enabled and available.
- Exact/reference agreement on local fixtures is a scaffold signal, not functional equivalence or production signoff.
