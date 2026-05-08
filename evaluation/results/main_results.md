# Main Results

| System | Issue Acc. | Action Acc. | Top-3 RCA | Evidence Quality |
| --- | ---: | ---: | ---: | ---: |
| Heuristic | TBD | TBD | TBD | TBD |
| Raw-log LLM | TBD | TBD | TBD | TBD |
| JasperLoop-DV | TBD | TBD | TBD | TBD |

## Scaffold Sanity Check

| System | Cases | Issue Acc. | Action Acc. | Notes |
| --- | ---: | ---: | ---: | --- |
| Heuristic baseline | 30 | 0.933 | 0.933 | Deterministic packet-metadata baseline; validates baseline plumbing, not final LLM performance. |
| Raw-log fallback | 30 | 0.633 | 0.633 | Deterministic raw JasperGold report/trace scaffold on `moore`, without hosted LLM. |
| Structured fallback agent | 30 | 1.000 | 1.000 | Deterministic structured scaffold; validates packet/evaluation plumbing, not final LLM performance. |

## Coverage Closure Scaffold

| System | Cases | Gap Type Acc. | Action Acc. | Wrong Test Suggestion Rate |
| --- | ---: | ---: | ---: | ---: |
| Raw-log fallback | 9 | 0.667 | 0.667 | 1.000 |
| JasperLoop-DV structured | 9 | 1.000 | 1.000 | 0.000 |

Detailed coverage closure results are tracked in `evaluation/results/coverage_closure_results.md`.
