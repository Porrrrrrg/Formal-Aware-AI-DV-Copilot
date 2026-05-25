# Evaluation

Evaluation results are separated by evidence source:

- deterministic scaffold: local fallback logic with no LLM call;
- real local LLM: a configured `JASPERLOOP_LLM_CMD` backend;
- replay: previously approved outputs replayed through local checkers;
- JasperGold-backed: formal tool results from a configured JasperGold environment.

The final curated result table is [final_results.md](../evaluation/results/final_results.md).

## Local Validation

```bash
python -m compileall copilot tools evaluation scripts
python -m pytest
python scripts/build_all_evidence_packets.py
python scripts/refresh_eval_results.py --allow-rebuild-packets
```

`refresh_eval_results.py` writes only `evaluation/results/final_results.md` in the final repository. Older per-experiment result Markdown files were merged into the final table and experiment history.

## Local Evaluation Runners

```bash
python evaluation/run_agent_eval.py --all-systems --out evaluation/results/agent_eval_local.json
python evaluation/run_coverage_eval.py --all-systems --out evaluation/results/coverage_eval_local.json
python evaluation/run_sva_eval.py --out evaluation/results/sva_eval_local.json
python evaluation/run_sva_repair_eval.py --out evaluation/results/sva_repair_local.json
```

These commands may write JSON files under `evaluation/results/`; those JSON outputs are ignored local artifacts unless explicitly curated.

## LLM Backend Gate

```bash
python scripts/doctor_llm_backend.py --json
python scripts/test_llm_backend_contract.py
```

A valid real-model backend must read prompts from stdin, write exactly one JSON object to stdout, and exit nonzero on failure. Fallback-only results are environment gate failures, not model performance.

## JasperGold Validation

Run only where JasperGold is available:

```bash
bash scripts/run_jasper_smoke.sh
bash scripts/run_jasper_sva_eval.sh
bash scripts/run_jasper_sva_repair_eval.sh
```

If `JASPER_BIN`, `JASPER_ENV`, and `jg` are unavailable, record JasperGold validation as not run. Do not create JasperGold-backed summaries from local scaffold or exact-match results.

## Required Metrics

Curated results should report, where applicable:

- JSON validity
- fallback rate
- LLM error rate
- hallucinated signal rate
- issue/action accuracy
- repair or exact-match success
- coverage gap/action accuracy
- JasperGold syntax, proof, falsified, undetermined, and vacuity counts

Proof pass is scoped to the harnesses, assumptions, and checked properties. It is not full semantic intent equivalence.
