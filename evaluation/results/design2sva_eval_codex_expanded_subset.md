# Design2SVA Results

## Summary

Mode: `real_llm`

| Metric | Value |
| --- | ---: |
| Cases | 12 |
| k | 3 |
| syntax@1 | 1.000 |
| syntax@k | 1.000 |
| proven@1 | 0.000 |
| proven@k | 0.000 |
| non_vacuous@k | 0.000 |
| antecedent_reachable@1 | 0.000 |
| antecedent_reachable@k | 0.000 |
| cover_reachable@k | 0.000 |
| proven_non_vacuous@k | 0.000 |
| reference_proven@1 | 0.000 |
| reference_non_vacuous@1 | 0.000 |
| reference_antecedent_reachable@1 | 0.000 |
| wrapper_parity_pass_rate | 0.000 |
| harness_reachability_status | not_run |
| root_cause_candidates | unknown=36 |
| root_cause_details | temporal_mismatch=29, unknown_signal=7 |
| Hallucinated signal rate | 0.194 |
| Fallback rate | 0.000 |
| Valid JSON rate | 1.000 |
| Average rounds | 0.000 |
| Repair success after feedback | 0.000 |
| Repaired proven_non_vacuous | 0.000 |

Formal metrics status: `not_run`.

## Boundaries

- Dry-run and replay rows validate local infrastructure and JSON contracts.
- They are not production signoff.
- `proven@*` and `non_vacuous@k` remain `0.000` with status `not_run`
  unless real JasperGold checks are explicitly enabled and available.
- Exact/reference agreement is a local scaffold signal, not semantic equivalence.
- Stage 11/12 root-cause labels are diagnostic candidates, not a claim that
  Design2SVA generation succeeded.
