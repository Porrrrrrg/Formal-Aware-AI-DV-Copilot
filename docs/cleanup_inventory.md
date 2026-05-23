# Cleanup Inventory

This inventory was produced from a read-only scan of the workspace before cleanup.

## Files To Keep

- `README.md`, `AGENTS.md`, `pyproject.toml`
- `benchmarks/` source collateral: RTL, formal harnesses, assumptions, properties, manifests, coverage plans, and case JSON
- `copilot/` agents, prompts, schemas, baselines, adapters
- `tools/` parsers, validators, evidence builders, JasperGold runner
- `evaluation/` runners, metrics, fixtures, curated Markdown summaries
- `jasper/common/` TCL flows
- `jasper/reports/.gitkeep`
- canonical docs under `docs/`

## Files To Move Or Archive

Workspace-level snapshot directories and generated bundles outside the active repository should remain outside Git or be archived as release artifacts:

- `Formal-Aware-AI-DV-Copilot-*-v1/`
- root `*.bundle`, `*.zip`, `*.tar`, `*_tmp.json`, and temporary run scripts
- `moore_artifacts_*`, `stage*_moore_artifacts/`, `stage5-cli-validation/`
- local model/cache/runtime folders

## Files To Gitignore

The repository ignores raw/generated outputs by default:

- `jasper/reports/` except `.gitkeep`
- `/reports/` generated report trees
- `local_reports/`, `artifacts/`, `runs/`, `logs/`
- `*.log`, `*.jou`, `*.rpt`, `*.vcd`, `*.fst`, `*.fsdb`, `*.wlf`, `*.trace`, `*.tmp`
- Python/test caches and build outputs

## Duplicate Docs To Merge

Canonical docs are now:

- `docs/architecture.md`
- `docs/methods.md`
- `docs/benchmark_catalog.md`
- `docs/evaluation.md`
- `docs/limitations_and_claims.md`
- `docs/artifact_policy.md`
- `docs/environment/jaspergold.md`
- the site-specific environment note under `docs/environment/`
- `docs/codex/`
- `docs/reports/`

Older `docs/design_doc.md`, `docs/progress_report.md`, `docs/final_report.md`, and `docs/codex_cli_usage.md` are compatibility notes.

## Host-Specific References To Rewrite

Project identity, architecture, README, general scripts, and result summaries should use repository-root and environment-variable wording. Site-specific host commands belong only in the environment note and compatibility wrappers.

## Benchmark And Result Gaps

- FVEval subset support must be reported as local data plumbing or proxy metrics unless the full official evaluation flow is reproduced.
- FIFO is optional benchmark collateral; result tables must say whether FIFO cases were included.
- Deterministic scaffold results must remain separate from Codex, replay, JasperGold-backed, and local Python results.
- Coverage witness extraction has a parser/interface path, but broader real-trace coverage remains pending until more fixtures and JasperGold runs are bound to manifests.
