# SVA Generation Results

| System | Cases | Syntax Scaffold | Exact Template Match | Hallucinated Signal Rate | Notes |
| --- | ---: | ---: | ---: | ---: | --- |
| Direct fallback | 27 | 1.000 | 0.222 | 0.000 | Deterministic intent-only scaffold; not JasperGold proof checked. |
| Structured fallback | 27 | 1.000 | 1.000 | 0.000 | Deterministic structured scaffold; validates generation/evaluation plumbing before LLM runs. |

These scaffold metrics check JSON plumbing, simple SVA shape, exact match to local reference templates, and invented signal identifiers. They are not a replacement for JasperGold syntax/proof/non-vacuity checks.
