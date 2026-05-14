# Design2SVA Results

## Summary

Mode: `replay`

| Metric | Value |
| --- | ---: |
| Cases | 3 |
| k | 3 |
| syntax@1 | 1.000 |
| syntax@k | 1.000 |
| proven@1 | 0.000 |
| proven@k | 0.000 |
| non_vacuous@k | 0.000 |
| Hallucinated signal rate | 0.000 |
| Fallback rate | 0.000 |
| Valid JSON rate | 1.000 |
| Average rounds | 0.000 |
| Repair success after feedback | 0.000 |

Formal metrics status: `not_run`.

## Boundaries

- Dry-run and replay rows validate local infrastructure and JSON contracts; they are not production signoff.
- `proven@*` and `non_vacuous@k` remain `0.000` with status `not_run` unless real JasperGold checks are explicitly enabled and available.
- Exact/reference agreement is a local scaffold signal for these fixtures, not a semantic equivalence result.
