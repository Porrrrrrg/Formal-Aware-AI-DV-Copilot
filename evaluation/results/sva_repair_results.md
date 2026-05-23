# SVA Repair Results

Local scaffold run:

```bash
python evaluation/run_sva_repair_eval.py --out evaluation/results/sva_repair_local.json
```

| System | Cases | Round-0 Syntax | Final Exact Match | Repair Success | Avg Rounds | Result Source |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| Structured fallback repair loop | 18 | 0.833 | 1.000 | 1.000 | 1.000 | deterministic scaffold |

JasperGold syntax/proof/vacuity re-check was not run in the current local environment. The repair set covers syntax errors, unknown signals, reset mistakes, overbroad assertions, and temporal/semantic assertion bugs across the arbiter, ready/valid buffer, and APB-lite benchmarks.

The final repair success rate demonstrates deterministic scaffold convergence to known-good templates. It is not Codex performance and not production signoff evidence.
