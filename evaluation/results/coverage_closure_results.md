# Coverage Closure Results

| System | Cases | Gap Type Acc. | Action Acc. | Wrong Test Suggestion Rate | Reachable Sequence Rate |
| --- | ---: | ---: | ---: | ---: | ---: |
| Raw-log fallback | 14 | 0.643 | 0.643 | 1.000 | 1.000 |
| JasperLoop-DV structured | 14 | 1.000 | 1.000 | 0.000 | 1.000 |

The coverage-only benchmark spans arbiter, ready/valid buffer, APB-lite, and optional FIFO cases. The raw-log fallback intentionally lacks coverage-plan intent and can suggest directed tests for illegal or invalid targets. The structured agent receives coverage-plan metadata and JasperGold reachability context, so it distinguishes reachable gaps from waiver/prove-unreachable cases in the scaffold evaluation.

The coverage runner also reports `source_counts`, `llm_success_rate`, `fallback_rate`, and `llm_error_rate`, so Codex-backed coverage experiments can be separated from deterministic fallback behavior.
