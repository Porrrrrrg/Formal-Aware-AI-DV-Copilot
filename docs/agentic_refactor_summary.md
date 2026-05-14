# Agentic Refactor Summary

## What Changed

- Added typed agent/evidence models in `app/models/agent.py` and compatibility
  exports in `copilot/schemas/models.py`.
- Added `copilot/backends` with a backend-neutral interface and a JasperGold
  facade that returns typed `BackendResult` objects.
- Added `copilot/retrieval` with a lightweight RTL index for module interfaces,
  assigns, always blocks, hierarchy, signal logic, and clock/reset candidates.
- Hardened JasperGold report and trace parsing for syntax errors, uncovered
  goals, parser warnings, hierarchical trace signals, and witness events.
- Extended coverage evidence with observed cover status, status source, and
  witness events where trace data exists.
- Brought `fifo_1r1w` into default triage, coverage, and result-refresh
  evaluation scopes.
- Added output-family accounting so deterministic fallback, raw-log LLM,
  structured LLM, and Jasper-feedback repair-loop rows are separable.
- Added focused regression tests for typed models, backend normalization,
  retrieval, parser/witness behavior, FIFO defaults, and output provenance.

## Commands Preserved

The existing local commands remain the validation targets:

```bash
python scripts/build_all_evidence_packets.py
python evaluation/run_agent_eval.py --all-systems --out evaluation/results/agent_eval_all_local.json
python evaluation/run_sva_eval.py --out evaluation/results/sva_eval_local.json
python evaluation/run_sva_repair_eval.py --out evaluation/results/sva_repair_local.json
python evaluation/run_coverage_eval.py --all-systems --out evaluation/results/coverage_eval_local.json
python scripts/refresh_eval_results.py
python scripts/run_codex_llm_eval.py --task healthcheck
```

## Remaining Evidence Needed

- Run the full validation block in an environment with the project Python
  dependencies available.
- Run Moore/JasperGold checks for any new generated SVA or coverage witness
  claims.
- Run real Codex subsets only with explicit external-send acknowledgement and
  report valid JSON, fallback, source, error, and hallucinated-signal metrics.
- Expand Design2SVA only as infrastructure unless JasperGold-backed functional
  evidence is recorded.
