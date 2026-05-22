# Evaluation

## Local Commands

```bash
python -m compileall copilot tools evaluation scripts
python scripts/build_all_evidence_packets.py
python evaluation/run_agent_eval.py --all-systems --out evaluation/results/agent_eval_all_local.json
python evaluation/run_coverage_eval.py --all-systems --out evaluation/results/coverage_eval_local.json
python evaluation/run_sva_eval.py --out evaluation/results/sva_eval_local.json
python evaluation/run_sva_repair_eval.py --out evaluation/results/sva_repair_local.json
python scripts/refresh_eval_results.py
```

Use `pytest` when test dependencies are installed.

## JasperGold Commands

Run only in an environment with JasperGold available:

```bash
bash scripts/run_jasper_smoke.sh
bash scripts/run_jasper_sva_eval.sh
bash scripts/run_jasper_sva_repair_eval.sh
```

If `JASPER_BIN` is not executable and no JasperGold environment is available, JasperGold validation should be recorded as not run.

Current local cleanup validation did not run JasperGold because `JASPER_BIN` and `JASPER_ENV` were unset and no `jg` executable was found on `PATH`.

The 2026-05-22 real LLM subset gate did not reach Codex model execution in this environment. `codex`/`codex.exe` resolved to the Codex Windows app package, but subprocess invocation failed with `Access is denied`; local Qwen healthcheck also reported `local_unavailable`. The generated Codex subset JSON files therefore record structured fallback behavior and must not be reported as Codex performance.

## Result Sources

Every result table should identify its source:

- `deterministic scaffold`: local fallback logic with no hosted model
- `Codex`: live Codex-backed run with prompt audit and external-send acknowledgement
- `replay`: previously approved model outputs replayed locally
- `JasperGold`: formal tool result from a configured JasperGold environment
- `local Python`: compile, schema, parser, or unit-test validation

Do not present deterministic scaffold metrics as Codex or hosted LLM performance.

## Required Metrics

Where applicable, result summaries should include:

- JSON validity
- fallback rate
- LLM error rate
- hallucinated signal rate
- syntax pass rate
- proof status
- vacuity status
- issue/action accuracy
- coverage witness availability

Curated Markdown summaries stay under `evaluation/results/`. Full JSON outputs, traces, logs, and raw reports are local artifacts unless explicitly selected for tracking.
