# Design2SVA Results

These results are generated from the retrieval-assisted Design2SVA scaffold. Rows are separated by artifact, provenance, and formal-check status so deterministic, replay, real LLM, and JasperGold-measured outcomes are not conflated.

## Infrastructure Sanity

Local scaffold rows used to validate parsing, schema, and replay plumbing before citing model or JasperGold behavior.

| Artifact | Row type | Mode | Cases | k | syntax@1 | syntax@k | proven@1 | proven@k | non_vacuous@k | valid_json | fallback | Source | Formal check | Signal |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | --- |
| design2sva_eval_local.json | deterministic | deterministic_scaffold | 3 | 3 | 1.000 | 1.000 | 0.000 | 0.000 | 0.000 | 1.000 | 1.000 | structured_fallback=9 | not_run | failures: passed=9 |
| design2sva_eval_replay_local.json | replay | replay | 3 | 3 | 1.000 | 1.000 | 0.000 | 0.000 | 0.000 | 1.000 | 0.000 | replay=9 | not_run | failures: passed=9 |

## Reference/Native Oracle

Reference and native-oracle controls are kept separate from generated-candidate rows so oracle/tooling checks do not overwrite LLM measurements.

| Artifact | Row type | Mode | Cases | k | syntax@1 | syntax@k | proven@1 | proven@k | non_vacuous@k | valid_json | fallback | Source | Formal check | Signal |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | --- |
| design2sva_eval_reference_oracle_local.json | reference oracle | reference_oracle | 3 | 1 | 1.000 | 1.000 | 0.000 | 0.000 | 0.000 | 1.000 | 0.000 | reference_oracle=3 | not_run | failures: not_run=3; root causes: unknown=3; harness: not_run=3 |
| design2sva_eval_reference_oracle_jasper.json | reference oracle | reference_oracle | 3 | 1 | 1.000 | 1.000 | 0.000 | 0.000 | 0.000 | 1.000 | 0.000 | reference_oracle=3 | JasperGold-measured | failures: unreachable_antecedent=2, unreachable_cover_goal=1; harness: unreachable=3 |
| design2sva_eval_reference_oracle_parity_local.json | reference oracle | reference_oracle | 3 | 1 | 1.000 | 1.000 | 0.000 | 0.000 | 0.000 | 1.000 | 0.000 | reference_oracle=3 | not_run | failures: not_run=3; root causes: unknown=3; harness: not_run=3 |
| design2sva_eval_reference_oracle_parity_jasper.json | reference oracle | reference_oracle | 3 | 1 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.000 | reference_oracle=3 | JasperGold-measured | failures: proven_non_vacuous=3; root causes: unknown=3; harness: not_run=1, reachable=2 |
| design2sva_eval_reference_oracle_rootcause_jasper.json | reference oracle | reference_oracle | 3 | 1 | 1.000 | 1.000 | 0.000 | 0.000 | 0.000 | 1.000 | 0.000 | reference_oracle=3 | JasperGold-measured | failures: unreachable_antecedent=2, unreachable_cover_goal=1; root causes: design2sva_embedding_bug=3; harness: not_run=1, unreachable=2 |
| design2sva_native_reference_oracle_jasper.json | native oracle | native_reference_oracle | 3 | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A | native_reference_oracle=3 | native JasperGold-measured | root causes: unknown=3; native proof: proven=3; native vacuity: not_run=3 |

## Expanded oracle validation

Stage 15 expanded native and wrapper reference-oracle controls are rendered separately from generated-candidate rows. Dry-run, replay, and real JasperGold outputs must not be collapsed into one result.

| Artifact | Row type | Mode | Cases | k | syntax@1 | syntax@k | proven@1 | proven@k | non_vacuous@k | valid_json | fallback | Source | Formal check | Signal |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | --- |
| design2sva_native_oracle_expanded_local.json | native oracle | design2sva_native_oracle_expanded | 12 | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A | native_reference_oracle=12 | local_dry_run | root causes: unknown=12; native proof: not_run=12; native vacuity: not_run=12 |
| design2sva_native_oracle_expanded_jasper.json | native oracle | design2sva_native_oracle_expanded | 12 | N/A | N/A | N/A | 1.000 | 1.000 | 0.000 | N/A | N/A | native_reference_oracle=12 | jasper_measured | root causes: unknown=12; native proof: proven=12; native vacuity: not_run=12 |
| design2sva_reference_oracle_expanded_local.json | reference oracle | design2sva_reference_oracle_expanded | 12 | 1 | N/A | N/A | 0.000 | 0.000 | 0.000 | 1.000 | 0.000 | reference_oracle=12 | local_dry_run | root causes: unknown=12; root details: formal_check_not_run=12; native proof: not_run=12; native vacuity: not_run=12 |
| design2sva_reference_oracle_expanded_jasper.json | reference oracle | design2sva_reference_oracle_expanded | 12 | 1 | N/A | N/A | 1.000 | 1.000 | 1.000 | 1.000 | 0.000 | reference_oracle=12 | jasper_measured | root causes: unknown=12; root details: reference_oracle_matches_native_formal_behavior=12; native proof: proven=12; native vacuity: not_run=12 |

## Real LLM Subset

Hosted-model subset rows are separated by whether JasperGold was run, so schema success is not conflated with measured proof quality.

| Artifact | Row type | Mode | Cases | k | syntax@1 | syntax@k | proven@1 | proven@k | non_vacuous@k | valid_json | fallback | Source | Formal check | Signal |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | --- |
| design2sva_eval_codex_subset.json | real LLM | real_llm | 3 | 3 | 1.000 | 1.000 | 0.000 | 0.000 | 0.000 | 1.000 | 0.000 | llm=9 | not_run | failures: passed=9, temporal_mismatch=9 |
| design2sva_eval_codex_jasper_subset.json | real LLM | real_llm | 3 | 3 | 1.000 | 1.000 | 0.000 | 0.000 | 0.000 | 1.000 | 0.000 | llm=9 | JasperGold-measured | failures: weak_vacuous_assertion=18 |

## JasperGold Fixed-Wrapper Rerun

Fixed-wrapper rows replay committed candidates through the corrected wrapper and report JasperGold-measured outcomes.

| Artifact | Row type | Mode | Cases | k | syntax@1 | syntax@k | proven@1 | proven@k | non_vacuous@k | valid_json | fallback | Source | Formal check | Signal |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | --- |
| design2sva_eval_reference_oracle_fixed_wrapper_sanity.json | reference oracle | reference_oracle_fixed_wrapper_sanity | 3 | 1 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.000 | reference_oracle=3 | JasperGold-measured | failures: proven_non_vacuous=3; root causes: unknown=3; root details: reference_oracle_matches_native_formal_behavior=3; backend: passed=3; harness: not_run=1, reachable=2 |
| design2sva_eval_codex_fixed_wrapper_rerun.json | replay of committed LLM candidates | committed_codex_candidate_replay | 3 | 3 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.000 | llm=9 | JasperGold-measured | failures: proven_non_vacuous=9; root causes: unknown=9; root details: assertion_proven_non_vacuous=9; backend: passed=9; harness: not_run=3 |
| design2sva_eval_antivacuity_codex_fixed_wrapper_rerun.json | replay of committed LLM candidates | committed_codex_candidate_replay | 3 | 5 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.000 | llm=15 | JasperGold-measured | failures: proven_non_vacuous=15; root causes: unknown=15; root details: assertion_proven_non_vacuous=15; backend: passed=15; harness: not_run=3 |

## Expanded Fixtures

Expanded anti-vacuity fixture rows are isolated from the original subset to avoid replacing earlier measurements.

| Artifact | Row type | Mode | Cases | k | syntax@1 | syntax@k | proven@1 | proven@k | non_vacuous@k | valid_json | fallback | Source | Formal check | Signal |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | --- |
| design2sva_eval_anti_vacuity_replay.json | replay | replay | 1 | 1 | 1.000 | 1.000 | 0.000 | 0.000 | 0.000 | 1.000 | 0.000 | replay=1 | replayed | failures: proven_non_vacuous=1, unreachable_antecedent=1 |
| design2sva_eval_anti_vacuity_jasper_subset.json | replay | replay | 3 | 3 | 1.000 | 1.000 | 0.000 | 0.000 | 0.000 | 1.000 | 0.000 | llm=9 | JasperGold-measured | failures: unreachable_antecedent=12, unreachable_cover_goal=6 |
| design2sva_eval_antivacuity_codex_new_subset.json | real LLM | real_llm | 3 | 5 | 1.000 | 1.000 | 0.000 | 0.000 | 0.000 | 1.000 | 0.000 | llm=15 | not_run | failures: not_run=15, temporal_mismatch=15 |
| design2sva_eval_antivacuity_codex_new_jasper_subset.json | replay | replay | 3 | 5 | 1.000 | 1.000 | 0.000 | 0.000 | 0.000 | 1.000 | 0.000 | llm=15 | JasperGold-measured | failures: unreachable_antecedent=20, unreachable_cover_goal=10 |
| design2sva_codex_replay_expanded_local.json | replay | committed_codex_expanded_replay | 3 | 3 | 1.000 | 1.000 | 0.000 | 0.000 | 0.000 | 1.000 | 0.000 | llm=9 | jasper_dry_run | failures: not_run=9, temporal_mismatch=9; root causes: unknown=18; root details: formal_check_not_run=9, temporal_mismatch=9; backend: dry_run=18; harness: not_run=3 |
| design2sva_codex_replay_expanded_jasper.json | replay | committed_codex_expanded_replay | 3 | 3 | 1.000 | 1.000 | 0.000 | 0.000 | 0.000 | 1.000 | 0.000 | llm=9 | jasper_dry_run | failures: not_run=9, temporal_mismatch=9; root causes: unknown=18; root details: formal_check_not_run=9, temporal_mismatch=9; backend: dry_run=18; harness: not_run=3 |

## Ablation Plan

Design2SVA ablation artifacts are rendered here when present; planned rows below reserve non-overlapping reporting slots for follow-up runs.

| Artifact | Row type | Mode | Cases | k | syntax@1 | syntax@k | proven@1 | proven@k | non_vacuous@k | valid_json | fallback | Source | Formal check | Signal |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | --- |
| design2sva_ablation_replay_local.json | replay | dry_run_replay_plan | 12 | 1 | N/A | N/A | N/A | N/A | N/A | 1.000 | 0.000 | ablation_plan=6 | not_run | none |

| Variant | Status | Isolation target |
| --- | --- | --- |
| No retrieval examples | planned | Isolate how much retrieval context affects valid JSON, syntax, and candidate diversity. |
| No JasperGold feedback repair | planned | Disable feedback-guided repair and compare repair_success_after_feedback plus non_vacuous@k. |
| No fixed wrapper | planned control | Compare against fixed-wrapper reruns to separate wrapper integration defects from generated SVA quality. |
| Reference/native oracle controls | measured controls above | Use oracle rows to bound harness, wrapper, and native-reference failures before attributing errors to the LLM. |

## Claim Boundaries

- Dry-run, replay, and deterministic scaffold rows do not measure hosted model quality.
- Real LLM rows measure schema-constrained hosted-model behavior only when `source_counts` records `llm` outputs and fallback is low.
- JasperGold-measured rows are the only rows where `proven@*` and `non_vacuous@k` should be cited as formal outcomes.
- Reference and native-oracle rows are infrastructure controls; exact/reference agreement on fixtures is not production signoff.
- Fixed-wrapper reruns isolate wrapper correctness from candidate generation quality.
- If expanded references prove non-vacuously with high native/wrapper parity, the expanded fixtures are valid for LLM evaluation.
- If expanded references fail, do not run the expanded LLM benchmark yet; repair the fixture, harness, or wrapper first.
