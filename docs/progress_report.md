# Progress Report

## Evidence Status

| Area | Status | Boundary |
| --- | --- | --- |
| Local DV benchmark | 53 labeled cases across `arbiter_rr2`, `rv_buffer`, `apb_regblock`, and `fifo_1r1w` | Labels are authored benchmark metadata |
| Evidence packets | Builder emits schema-compatible packets with Jasper summaries, RTL context, coverage evidence, vacuity context, and optional witness events | Packet quality depends on available reports/traces |
| JasperGold backend | Typed `BackendResult` facade added for syntax, proof, vacuity, CEX paths, raw logs, and structured errors | Existing CLI scripts remain compatibility wrappers |
| Retrieval | `copilot/retrieval` extracts module interfaces, assigns, always blocks, hierarchy, signal logic, and clock/reset candidates | Regex fallback only; no ProofLoop performance claim |
| Evaluation provenance | Runners report source/fallback/error metrics and output-family counts | Deterministic fallback is not hosted LLM performance |
| FVEval subset | Local-compatible subset runner and prompt-sanitization checks exist | Not official FVEval and no commercial equivalence flow |

## Local Evaluation Commands

```bash
python scripts/build_all_evidence_packets.py
python evaluation/run_agent_eval.py --all-systems --out evaluation/results/agent_eval_all_local.json
python evaluation/run_sva_eval.py --out evaluation/results/sva_eval_local.json
python evaluation/run_sva_repair_eval.py --out evaluation/results/sva_repair_local.json
python evaluation/run_coverage_eval.py --all-systems --out evaluation/results/coverage_eval_local.json
python scripts/refresh_eval_results.py
python scripts/run_codex_llm_eval.py --task healthcheck
```

Additional local checks:

```bash
python -m pytest -q
python -m ruff check .
python evaluation/run_fveval_subset.py
```

## Prompt Audit Before External Calls

```bash
python scripts/export_codex_prompts.py --task all --limit 3 --summary-only
python scripts/export_codex_prompts.py --task triage --limit 2 --redact-evidence --summary-only
python scripts/run_codex_llm_eval.py --task healthcheck
```

Do not run benchmark tasks with `--acknowledge-external-send` unless the data
export has been explicitly approved. Benchmark tasks may send SVA snippets,
evidence packets, Jasper summaries, RTL excerpts, coverage goals, and directed
sequence context to the configured LLM backend.

## Optional Codex Subsets

```bash
python scripts/run_codex_llm_eval.py --task sva_repair --limit 3 --acknowledge-external-send
python scripts/run_codex_llm_eval.py --task triage --limit 3 --acknowledge-external-send
python scripts/run_codex_llm_eval.py --task coverage --limit 3 --acknowledge-external-send
```

Allowed claims are limited to the recorded subset, model snapshot, prompt
version, source counts, valid JSON rate, fallback rate, error rate, and
hallucinated-signal rate.

## JasperGold Evaluation

```bash
python -m app.cli workflow repair --dry-run --out-dir artifacts/jasper_handoff/repair
bash scripts/run_jasper_smoke.sh
bash scripts/run_jasper_sva_eval.sh
bash scripts/run_jasper_sva_repair_eval.sh
```

Configured JasperGold host example:

```bash
bash scripts/run_jasper_smoke.sh
```

## Roadmap

| Phase | Goal | Evidence Gate |
| --- | --- | --- |
| Phase 1 architecture | Typed evidence models, backend boundary, retrieval index, parser hardening | Local tests and preserved CLI commands |
| Phase 2 real Codex subset | 3-case subsets for repair, triage, and coverage | Explicit external-send acknowledgement plus provenance metrics |
| Phase 3 FVEval/FIFO/vacuity | Broader FIFO, vacuity, false-positive, and FVEval-compatible cases | FV-backed functional/formal scoring where possible |
| Phase 4 repo-scale metadata | Retrieval over larger RTL repos with structural metadata | AST/slang integration, hierarchy queries, and JasperGold feedback loops |

Scaffold success, deterministic fallback, replay output, dry-run manifests, and
local-compatible subset completion must not be described as real LLM quality,
JasperGold proof, or production readiness. Real LLM results require recorded
backend/source/error/fallback fields. Real formal claims require imported
JasperGold summaries tied to checked harnesses and assumptions.
