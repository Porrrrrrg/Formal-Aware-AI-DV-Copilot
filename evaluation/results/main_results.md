# Main Results

| System | Issue Acc. | Action Acc. | Top-3 RCA | Evidence Quality |
| --- | ---: | ---: | ---: | ---: |
| Heuristic | TBD | TBD | TBD | TBD |
| Raw-log LLM | TBD | TBD | TBD | TBD |
| JasperLoop-DV | TBD | TBD | TBD | TBD |

## Scaffold Sanity Check

| System | Cases | Issue Acc. | Action Acc. | Hallucinated Signal | Notes |
| --- | ---: | ---: | ---: | ---: | --- |
| Heuristic baseline | 53 | 0.226 | 0.226 | 0.000 | Deterministic packet-metadata baseline; validates baseline plumbing, not final LLM performance. |
| Raw-log fallback | 53 | 0.396 | 0.396 | 0.000 | Deterministic raw JasperGold report/trace scaffold, without hosted LLM. |
| Structured fallback agent | 53 | 0.906 | 0.906 | 0.000 | Deterministic structured scaffold; validates packet/evaluation plumbing, not final LLM performance. |

Source/fallback metrics for Codex-backed runs are tracked in `evaluation/results/output_quality_results.md`.

## Coverage Closure Scaffold

| System | Cases | Gap Type Acc. | Action Acc. | Wrong Test Suggestion Rate |
| --- | ---: | ---: | ---: | ---: |
| Raw-log fallback | 14 | 0.643 | 0.643 | 1.000 |
| JasperLoop-DV structured | 14 | 1.000 | 1.000 | 0.000 |

Detailed coverage closure results are tracked in `evaluation/results/coverage_closure_results.md`.
