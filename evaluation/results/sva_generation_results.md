# SVA Generation Results

| System | Cases | Syntax Scaffold | Exact Template Match | Hallucinated Signal Rate | JG Syntax | JG Proven | JG Vacuous |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Direct fallback | 27 | 1.000 | 0.222 | 0.000 | 1.000 | 1.000 | 0.000 |
| Structured fallback | 27 | 1.000 | 1.000 | 0.000 | 1.000 | 1.000 | 0.000 |

JasperGold re-check was run on `moore` with `evaluation/run_sva_eval.py --jasper-check`. The direct fallback's low exact-match rate despite full JasperGold proof pass is a useful sanity warning: formal proof of a generated assertion on correct RTL is necessary, but not sufficient to establish semantic equivalence to the requested intent.
