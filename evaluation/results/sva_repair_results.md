# SVA Repair Results

| System | Cases | Round-0 Syntax | Final Exact Match | Repair Success | Avg Rounds |
| --- | ---: | ---: | ---: | ---: | ---: |
| Structured fallback + JasperGold feedback | 18 | 0.611 | 1.000 | 1.000 | 1.000 |

JasperGold re-check was run on `moore` with `evaluation/run_sva_repair_eval.py --jasper-check`. The 18 repair cases cover syntax errors, unknown signals, reset mistakes, overbroad assertions, and temporal/semantic assertion bugs across the arbiter, ready/valid buffer, and APB-lite benchmarks.

The low round-0 syntax rate is expected: the repair set intentionally injects malformed or tool-rejected assertions. The final repair success rate demonstrates that the loop plumbing can consume JasperGold feedback and converge to the known-good SVA template in the deterministic fallback mode.
