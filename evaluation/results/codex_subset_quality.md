# Codex/LLM Subset Quality Gate

This file is a curated gate summary. It separates real LLM success from deterministic fallback behavior.

Gate result: failed. The 3+3+3 subset reached a real local Qwen backend through `JASPERLOOP_LLM_CMD`, but failure-triage quality did not satisfy the full-run gate.

Backend route:

- Codex CLI route: unavailable on this Windows subprocess path because the Windows app package `codex.exe` still reports `permission_denied`.
- Generic command route: passed doctor and contract using `JASPERLOOP_LLM_CMD=python D:\AI-DV\qwen_json_backend.py`.
- Model endpoint: local vLLM OpenAI-compatible server at `http://127.0.0.1:8000/v1`, served model `Qwen/Qwen3-14B-AWQ`.
- Result type: real local Qwen subset result, not Codex CLI performance and not JasperGold-backed performance.

| Task | Cases | LLM Success | Fallback Rate | LLM Error Rate | Hallucinated Signal Rate | Accuracy Metric |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| SVA repair | 3 | 1.000 | 0.000 | 0.000 | 0.000 | final exact match 0.667 |
| Failure triage | 3 | 0.667 | 0.333 | 0.333 | 0.333 | issue/action 0.667/0.667 |
| Coverage closure | 3 | 1.000 | 0.000 | 0.000 | n/a | gap/action 1.000/1.000 |

Gate policy:

- JSON validity below 0.90: stop full run.
- Fallback rate above 0.25: stop full run.
- Hallucinated signal rate above 0.10: stop full run.
- Fallback-only results are failed environment gates, not model performance.

Real LLM performance requires outputs with `source`/`output_source` equivalent to `llm` and no fallback error.

Failure-triage gate status:

- JSON validity was 0.667, below the 0.90 threshold.
- Fallback rate was 0.333, above the 0.25 threshold.
- Hallucinated signal rate was 0.333, above the 0.10 threshold.

Full benchmark status: not allowed from this run. The next step is to improve the noninteractive JSON backend behavior for triage or use a stronger subprocess-callable local/backend model, then rerun only the subset gate.
