# SVA Generation Results

Local scaffold run:

```bash
python evaluation/run_sva_eval.py --out evaluation/results/sva_eval_local.json
```

| System | Cases | Syntax Scaffold | Exact Template Match | Hallucinated Signal Rate | Result Source |
| --- | ---: | ---: | ---: | ---: | --- |
| Direct fallback | 27 | 1.000 | 0.222 | 0.000 | deterministic scaffold |
| Structured fallback | 27 | 1.000 | 1.000 | 0.000 | deterministic scaffold |

JasperGold syntax/proof/vacuity re-check was not run in the current local environment. A proof pass, when available, is necessary evidence for a generated assertion but is not sufficient to establish semantic equivalence to the requested intent.
