# Repository Map

This map describes the Stage 5 repository layout and the ownership boundary for
repo hygiene work. It is descriptive only; it does not supersede release
ledgers, benchmark manifests, or experiment reports.

## Source And Runtime

| Path | Purpose | Hygiene notes |
| --- | --- | --- |
| `app/` | CLI, workflow orchestration, typed models, retrieval, local LLM integration, and intent-alignment entry points. | Source code. Keep behavior changes in feature PRs, not repo cleanup PRs. |
| `copilot/` | Agent prompts, deterministic baselines, LLM adapters, and JSON response schemas. | Source code and prompt contracts. Prompt/eval changes must update relevant tests and reports. |
| `core/` | Core typed IR and shared domain models. | Source code. Treat as shared API surface. |
| `adapters/` | Formal-tool adapter interfaces and smoke integrations. | Source code. Tool output should remain summarized or fixture-scoped. |
| `tools/` | Jasper runners, parsers, evidence packet builders, validators, and trace utilities. | Source code. Raw tool outputs belong in ignored local artifact paths. |
| `scripts/` | Convenience scripts for evaluations, demos, evidence packets, and project setup. | Source code. Scripts should default to explicit output paths and avoid committing raw outputs. |
| `ops/` | Local service operations material, including local LLM serving docs and healthcheck helper. | Operational docs/scripts. Secrets and machine-local configs stay untracked. |

## Benchmarks, Fixtures, And Examples

| Path | Purpose | Hygiene notes |
| --- | --- | --- |
| `benchmarks/` | Canonical RTL DV benchmark assets, specs, SVA, manifests, coverage plans, local-DV assets, and FVEval subset data. | Research evidence. Do not delete or relabel benchmark assets in hygiene-only PRs. |
| `examples/` | Demo workflow fixtures and sanitized sample verifier outputs. | Demo fixtures. Keep examples that are referenced by docs or tests. |
| `tests/` | Unit, contract, workflow, adapter, retrieval, and repo hygiene tests. | Test code. Hygiene tests protect tracked-file boundaries and documentation entry points. |

## Documentation

| Path | Purpose | Hygiene notes |
| --- | --- | --- |
| `README.md` | Project overview and legacy quick-start material. | User-facing entry point. Keep high-level and link to detailed docs where possible. |
| `docs/` | Architecture, CLI/workflow usage, local LLM, security, review, research, demo, repo map, and artifact policy docs. | Current docs should avoid depending on machine-specific paths. Historical notes can keep original context. |

## Reports And Evidence

| Path | Purpose | Hygiene notes |
| --- | --- | --- |
| `reports/index.md` | Human-readable index for report families and their retention status. | Add new report families here when they support claims or release gates. |
| `reports/release/` | Stage checkpoints, release ledgers, and artifact inventories. | Preserved evidence. Do not delete in repo cleanup PRs. |
| `reports/status/` | Gate status, blockers, audits, and coordination reports. | Historical unless marked current in the index. Keep old branch references as evidence. |
| `reports/jasper/` | Sanitized Jasper summaries and manifests. | Preserved evidence. Raw `.log`, `.rpt`, traces, `jgproject/`, and license output stay untracked. |
| `reports/workflows/` | Workflow smoke and end-to-end demo summaries/manifests. | Preserved evidence. |
| `reports/alignment/` | Intent-alignment smoke evidence. | Preserved evidence. Generated JSONL should be indexed before any archival move. |
| `reports/research/` | Research summaries, risk registers, plans, and generated run snapshots. | Preserved evidence for now. Generated payloads are archive candidates only after indexing and owner approval. |
| `reports/eval/` | Evaluation run snapshots. | Preserved evidence for now. Avoid duplicating canonical benchmark assets in future work. |
| `reports/local_llm/` | Local LLM and Qwen bring-up/readiness evidence. | Owned by local-LLM/Qwen work. Repo hygiene work should not edit these files. |

## Local-Only Paths

The following are protected by ignore rules and repo hygiene tests:

- `jasper/reports/**`
- `artifacts/**`
- trace directories such as `traces/`, `trace/`, `trace_*`, and `*_trace/`
- Python caches and virtual environments
- raw EDA outputs such as `.log`, `.rpt`, `.jou`, `.vcd`, `.fsdb`, and `.wlf`
- raw local LLM logs and model caches

See `docs/artifact_policy.md` for retention rules.
