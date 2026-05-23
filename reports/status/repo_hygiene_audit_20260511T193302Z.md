# Repo Hygiene Audit - 2026-05-11T19:33:02Z

Branch: `stage5/repo-hygiene-audit`
Base observed: `origin/main` at `5c3da97ef627fb0df6f52de18760406f847d77eb`
Scope: audit only. No files were deleted and no code behavior was changed.

## Method

This audit used tracked files from `git ls-files`, repository text scans with
`rg`, size checks from the local filesystem, and targeted checks for raw
JasperGold outputs, trace directories, cache directories, local environment
files, stale branch/worktree references, absolute machine paths, and report
indexing gaps.

Qwen report files under `reports/local_llm/` were treated as read-only audit
inputs and were not edited.

## Tree Summary

| Root | Tracked files | Tracked dirs | Primary contents |
| --- | ---: | ---: | --- |
| `app/` | 18 | 5 | CLI, workflow orchestration, local LLM backend, typed app models, retrieval, intent alignment |
| `copilot/` | 29 | 6 | Agent implementations, deterministic baselines, LLM adapters, prompts, response schemas |
| `benchmarks/` | 124 | 30 | RTL DV benchmark cases, specs, RTL variants, SVA, manifests, coverage plans, local/FVEval subsets |
| `jasper/` | 6 | 2 | JasperGold TCL helpers plus ignored `jasper/reports/` placeholder |
| `tools/` | 12 | 1 | Jasper runners/parsers, evidence packet builders, validators, trace and coverage utilities |
| `scripts/` | 11 | 1 | Evaluation, evidence, prompt export, Moore, and demo convenience scripts |
| `docs/` | 21 | 8 | Architecture, CLI/workflow usage, local LLM, security, review, research, demo docs |
| `reports/` | 106 | 16 | Historical audit/status/release/research/eval/Jasper/workflow/alignment report artifacts |
| `examples/` | 5 | 1 | End-to-end SVA repair workflow fixture and sanitized verifier sample |
| `ops/` | 6 | 1 | Local LLM serving docs, scripts, env example, healthcheck |
| `tests/` | 20 | 4 | CLI, workflow, schema, adapter, retrieval, benchmark, local LLM, and contract tests |

## Classification

| Class | Current paths | Audit notes |
| --- | --- | --- |
| Source code | `app/`, `copilot/`, `tools/`, `scripts/`, `adapters/`, `core/`, `evaluation/`, `ops/local-llm/healthcheck.py`, `tests/` | Active Python and shell code. No behavior changes made in this PR. |
| Benchmark assets | `benchmarks/*`, `benchmarks/local_dv/*`, `benchmarks/fveval_subset/*` | Canonical benchmark cases, RTL, specs, manifests, smoke assets, and symbol/registry data. |
| Test fixtures | `benchmarks/lean_smt_smoke/*`, `examples/workflows/sva_repair_demo/*`, selected `tests/**` inline fixtures | Fixtures are intentionally tracked and used by tests/workflow demos. |
| Docs | `README.md`, `docs/**`, `ops/local-llm/*.md`, `examples/**.md` | Several docs overlap with workflow/local-Qwen/demo topics and should be indexed or consolidated later. |
| Sanitized reports | `reports/jasper/*.md`, `reports/jasper/*.json`, `reports/workflows/*`, `reports/alignment/*`, `reports/release/*`, `reports/fveval/*` | Mostly bounded summaries/manifests. Jasper summaries are sanitized references, not raw `.rpt`/`.log` files. |
| Local-only generated artifacts | `reports/research/runs/**`, `reports/eval/local_dv/run_*/**`, `reports/repair/artifacts/*.jsonl`, `reports/alignment/*.jsonl`, `reports/local_llm/qwen_health.jsonl` | These are generated payloads rather than source. Some may belong outside the long-term tracked tree or behind an artifact policy. |
| Stale reports | `reports/status/stage3_*`, `reports/status/stage4_*`, `reports/review/pr_*`, older `reports/audits/*`, older research plans | Useful historical evidence, but they reference old branches, worktrees, blockers, or pre-merge state. Mark as historical if retained. |
| Duplicate docs | `README.md` vs `docs/workflow_usage.md`; `docs/e2e_demo.md` vs `examples/workflows/sva_repair_demo/README.md`; `docs/local_qwen_workflow.md` vs `docs/local-llm/qwen_3090ti.md` vs `ops/local-llm/README.md`; `docs/cli_usage.md` vs `docs/codex_cli_usage.md` | Not exact duplicates, but overlapping user-facing entry points can drift. |
| Possible archival material | `reports/audits/*`, `reports/research/runs/**`, `reports/review/*`, old gate/status reports | Candidate for a documented archive namespace or external release artifact store. |

## Hygiene Checks

| Check | Result | Evidence |
| --- | --- | --- |
| Raw Jasper logs accidentally tracked | No tracked `.log`, `.rpt`, `.jou`, `.vcd`, `.fsdb`, or `.wlf` files found. | `git ls-files` extension/pattern scan returned no tracked raw EDA output files. |
| Trace directories | No tracked `traces/` directories found. | Recursive directory scan found no tracked or present `traces/` directory. |
| Large generated artifacts | No tracked file exceeds 1 MB; seven files exceed 100 KB. | Largest tracked file is `reports/research/runs/20260510T214913Z/triage_ablation.json` at 439,964 bytes. |
| `__pycache__` | None tracked or present in this worktree. | Directory and tracked-file scans were clean. |
| `.venv` or environment files | No tracked `.venv`, `venv`, `env`, `.env`, or local config files. | `.gitignore` protects these; only `ops/local-llm/env.example` is tracked intentionally. |
| Stale branch/worktree references | Present in historical reports/docs. | Examples include `docs/agents/task_graph.md`, `reports/status/integration_plan_20260510T221015Z.md`, `reports/status/stage3_gate_kickoff_20260511T030746Z.md`, and `reports/status/stage4_second_wave_gate_20260511T141346Z.md`. |
| Machine-specific absolute paths | Present mostly in historical manifests/reports. | Examples include `D:\AI-DV\...`, `C:\Users\...`, `/home/esf2634/...`, `/tmp/...` in `reports/alignment/*`, `reports/research/runs/**/run_manifest.json`, `reports/jasper/*manifest*.json`, and older review/status docs. |
| Report files that should be indexed | No central `reports/INDEX.md` or machine-readable report registry exists. | `reports/` has 106 tracked files across 16 categories. |

## Large Tracked Files

Tracked files at or above 100 KB:

| Path | Size bytes | Classification |
| --- | ---: | --- |
| `reports/research/runs/20260510T214913Z/triage_ablation.json` | 439,964 | Local generated research payload |
| `reports/research/runs/20260510T214913Z/triage_all_systems.json` | 200,193 | Local generated research payload |
| `reports/research/runs/20260510T214913Z/sva_repair_ablation.json` | 166,266 | Local generated research payload |
| `reports/eval/local_dv/run_20260511T000415Z_0b7d76718814_2e9785/symbol_index.json` | 119,362 | Generated eval snapshot |
| `benchmarks/local_dv/symbol_index.json` | 119,362 | Benchmark/retrieval asset |
| `reports/jasper/sva_repair_ablation_final_proof_manifest_20260511T143254Z.json` | 113,928 | Sanitized Jasper manifest |
| `benchmarks/fveval_subset/cases.json` | 112,044 | Benchmark subset asset |

## Report Indexing Gaps

The repository has valuable report families but no stable index tying them to
stage, claim boundary, source command, owning branch, and replacement status.
High-value index candidates:

- Release ledgers/checkpoints: `reports/release/stage3_*`, `reports/release/stage4_*`.
- Current workflow evidence: `reports/workflows/e2e_demo_*`, `reports/workflows/workflow_smoke_*`.
- Current alignment evidence: `reports/alignment/intent_alignment_*`.
- Jasper evidence summaries/manifests: `reports/jasper/*summary*.md`, `reports/jasper/*manifest*.json`.
- Historical gate/status reports: `reports/status/*.md`.
- Historical audit reports: `reports/audits/*`.
- Local generated payload groups: `reports/research/runs/**`, `reports/eval/local_dv/run_*/**`, `reports/repair/artifacts/*.jsonl`.

## Findings

1. Raw EDA outputs are currently protected and no accidental raw JasperGold log
   or trace files were found in the tracked tree.
2. The `reports/` tree has grown into a mixed store of release evidence,
   sanitized manifests, local generated payloads, blockers, reviews, and old
   coordination reports. This is the primary cleanup target.
3. Historical reports contain many absolute machine paths and old branch names.
   They are acceptable as historical evidence but should not be used as current
   operational instructions without an index/status field.
4. Some generated JSON/JSONL report payloads are large enough to justify an
   artifact retention policy even though they are not currently oversized for
   git.
5. User-facing documentation now has overlapping entry points for CLI,
   workflow, demo, and local backend usage. A docs index and owner map would
   reduce drift.

## Limitations

- This was a static repository hygiene audit only.
- No semantic validation of every historical report claim was performed.
- No deletion, archive move, index creation, or behavior change was performed.
- Qwen report files were not edited.
