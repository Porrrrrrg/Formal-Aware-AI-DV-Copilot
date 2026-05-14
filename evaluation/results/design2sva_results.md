# Design2SVA Results

These results are generated from the local retrieval-assisted Design2SVA scaffold. They are infrastructure and replay/dry-run evidence unless the run mode records real LLM and JasperGold execution.

## Local Summary

| Metric | Value |
| --- | ---: |
| Mode | deterministic_scaffold |
| Cases | 3 |
| k | 3 |
| syntax@1 | 1.000 |
| syntax@k | 1.000 |
| proven@1 | 0.000 |
| proven@k | 0.000 |
| non_vacuous@k | 0.000 |
| hallucinated_signal_rate | 0.000 |
| fallback_rate | 1.000 |
| valid_json_rate | 1.000 |
| average_rounds | 0.000 |
| repair_success_after_feedback | 0.000 |

## Provenance

- Source counts: structured_fallback=9
- Failure categories: passed=9
- Formal metrics status: `not_run`

## Claim Boundary

- Dry-run, replay, and deterministic scaffold rows do not measure hosted model quality.
- `proven@*` and `non_vacuous@k` are only meaningful when real JasperGold checks are enabled and available.
- Exact/reference agreement on local fixtures is a scaffold metric, not functional equivalence or production signoff.
