# Coverage Closure Results

| System | Cases | Gap Type Acc. | Action Acc. | Wrong Test Suggestion Rate | Reachable Sequence Rate |
| --- | ---: | ---: | ---: | ---: | ---: |
| Raw-log fallback | 9 | 0.667 | 0.667 | 1.000 | 1.000 |
| JasperLoop-DV structured | 9 | 1.000 | 1.000 | 0.000 | 1.000 |

The coverage-only benchmark has 9 cases across arbiter, ready/valid buffer, and APB-lite: 6 reachable coverage gaps and 3 invalid or unreachable coverage goals. The raw-log fallback intentionally lacks coverage-plan intent and therefore suggests directed tests for all goals, including illegal or invalid targets. The structured agent receives coverage-plan metadata and JasperGold reachability context, so it distinguishes reachable gaps from waiver/prove-unreachable cases in the scaffold evaluation.
