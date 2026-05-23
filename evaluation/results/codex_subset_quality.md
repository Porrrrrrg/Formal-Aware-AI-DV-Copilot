# Codex/LLM Subset Quality Gate

This file is a curated gate summary. It separates real LLM success from deterministic fallback behavior.

Gate result: passed; full benchmark is allowed next but was not run.

Backend route: generic `JASPERLOOP_LLM_CMD` real local/backend LLM route.
Model endpoint: Qwen/Qwen3-14B-AWQ at `http://127.0.0.1:8000/v1`.
Result type: real local/backend LLM subset gate, not Codex CLI performance and not JasperGold-backed performance.

| Task | Cases | Valid JSON | LLM Success | Fallback Rate | LLM Error Rate | Hallucinated Signal Rate | Accuracy Metric |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| SVA repair | 3 | 1.000 | 1.000 | 0.000 | 0.000 | 0.000 | final exact match 0.667 |
| Failure triage | 3 | 1.000 | 1.000 | 0.000 | 0.000 | 0.000 | issue/action 0.667/0.667 |
| Coverage closure | 3 | 1.000 | 1.000 | 0.000 | 0.000 | n/a | gap/action 1.000/1.000 |

Gate policy:

- JSON validity below 0.90: stop full run.
- Fallback rate above 0.25: stop full run.
- Hallucinated signal rate above 0.10: stop full run.
- Fallback-only results are failed environment gates, not model performance.

Real LLM performance requires outputs with `source`/`output_source` equivalent to `llm` and no fallback error.
