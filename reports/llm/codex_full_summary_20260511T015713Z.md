# Codex Full Benchmark Summary

Run UTC: 2026-05-11T01:57:13Z
Branch: `stage/codex-full-eval`
Benchmark input SHA: `dec371bd7d4eb9aacf80a28ffc300914a7b45540`
Manifest: `reports/llm/codex_full_manifest_20260511T015713Z.json`
Error cases: `reports/llm/codex_full_error_cases_20260511T015713Z.md`

This is a real Codex-backed benchmark measurement. It is not a production-readiness claim and does not compare against Qwen. Qwen was not run.

## Scope Notes

- The exact requested task commands were run first. The wrapper still injects its default `--limit 3`, so those commands exercised three cases per task.
- To satisfy the full benchmark goal, an explicit full pass was then run with `--limit 999` and separate `*_codex_full.json` outputs.
- Metrics below use the explicit full pass: 18 SVA repair cases, 30 triage cases, and 9 coverage cases.
- Codex LLM outputs are reported separately from deterministic fallback results. The full pass had no fallback outputs.
- SVA repair outcomes are scaffold-level final outcomes. No live JasperGold final proof was run, so `proven_final` is 0.0 by evaluator output.

## Commands Run

| Step | Command | Result |
| --- | --- | --- |
| Preflight | `.venv\Scripts\python.exe -m pytest -q` | Passed, 67 tests |
| Preflight | `.venv\Scripts\python.exe -m ruff check .` | Passed |
| Prompt audit | `.venv\Scripts\python.exe scripts/export_codex_prompts.py --task all --limit 3 --summary-only` | Passed, 9 prompts |
| Healthcheck | `.venv\Scripts\python.exe scripts/run_codex_llm_eval.py --task healthcheck` | Passed, valid JSON |
| Requested task | `.venv\Scripts\python.exe scripts/run_codex_llm_eval.py --task sva_repair --acknowledge-external-send` | Passed, 3 cases due runner default |
| Requested task | `.venv\Scripts\python.exe scripts/run_codex_llm_eval.py --task triage --acknowledge-external-send` | Passed, 3 cases due runner default |
| Requested task | `.venv\Scripts\python.exe scripts/run_codex_llm_eval.py --task coverage --acknowledge-external-send` | Passed, 3 cases due runner default |
| Full task | `.venv\Scripts\python.exe scripts/run_codex_llm_eval.py --task sva_repair --limit 999 --out evaluation/results/sva_repair_codex_full.json --acknowledge-external-send` | Passed, 18 cases |
| Full task | `.venv\Scripts\python.exe scripts/run_codex_llm_eval.py --task triage --limit 999 --out evaluation/results/agent_eval_codex_full.json --acknowledge-external-send` | Passed, 30 cases |
| Full task | `.venv\Scripts\python.exe scripts/run_codex_llm_eval.py --task coverage --limit 999 --out evaluation/results/coverage_eval_codex_full.json --acknowledge-external-send` | Passed, 9 cases |
| Prompt audit | `.venv\Scripts\python.exe scripts/export_codex_prompts.py --task all --summary-only` | Passed, 9 prompts |

Final post-report checks are recorded in the manifest after report generation.

## Prompt Audit Summary

- Prompts exported: 9
- Prompt task mix: 3 SVA repair, 3 triage, 3 coverage
- Max prompt size: 3534 characters
- Total approximate tokens: 4708
- Prompts with gold labels: 0
- Prompts with RTL context: 0
- Prompts with Jasper evidence: 9

## Aggregate Metrics

| Metric | Value |
| --- | ---: |
| Cases attempted | 57 |
| LLM adapter outputs | 71 |
| Valid JSON rate | 71/71 = 100.0% |
| Fallback rate | 0/71 = 0.0% |
| LLM error rate | 0/71 = 0.0% |
| Hallucinated signal rate, defined tasks | 0/48 = 0.0% |
| Schema drift count | 0 |

## Task Results

| Task | Cases | LLM Outputs | Valid JSON | Fallback | LLM Error | Hallucinated Signal | Main Accuracy |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| SVA repair | 18 | 32 | 100.0% | 0.0% | 0.0% | 0.0% | 11/18 repair success |
| Triage | 30 | 30 | 100.0% | 0.0% | 0.0% | 0.0% | 28/30 issue and action accuracy |
| Coverage | 9 | 9 | 100.0% | 0.0% | 0.0% | N/A | 9/9 gap and action accuracy |

## SVA Repair Metrics

| Metric | Value |
| --- | ---: |
| Repair success | 11/18 = 61.1% |
| Proven final | 0/18 = 0.0% |
| Final exact match | 11/18 = 61.1% |
| Average rounds to success | 1.0 |
| Syntax pass at round 0 | 15/18 = 83.3% |
| Source counts | `llm`: 32 |

## Triage Metrics

| Metric | Value |
| --- | ---: |
| Issue type accuracy | 28/30 = 93.3% |
| Next action accuracy | 28/30 = 93.3% |
| Source counts | `llm`: 30 |

## Coverage Metrics

| Metric | Value |
| --- | ---: |
| Coverage gap accuracy | 9/9 = 100.0% |
| Coverage action accuracy | 9/9 = 100.0% |
| Wrong test suggestion rate | 0/3 = 0.0% |
| Reachable sequence presence | 6/6 = 100.0% |
| Source counts | `llm`: 9 |

## Artifact Trace

Raw local full-pass artifacts are ignored generated outputs and were not selected for commit.

| Path | SHA256 | Size |
| --- | --- | ---: |
| `evaluation/results/sva_repair_codex_full.json` | `D8B66A5E8C7BE4CCEA2D2EB1A0FD78EA9A4FD83745DA0BC98015AC2F0706E867` | 60648 bytes |
| `evaluation/results/agent_eval_codex_full.json` | `CD9FEA5BC03B96BB75242308B7518B57DED73E7D23CF3B5CDEDF01D676A8679D` | 106667 bytes |
| `evaluation/results/coverage_eval_codex_full.json` | `63F858DCF4E5ADB07434811503DD81546744F5E8DC397D79DD6DF38E27708EF0` | 25692 bytes |

