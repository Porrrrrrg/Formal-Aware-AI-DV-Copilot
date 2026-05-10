# Integration Plan - 20260510T221015Z

## Freeze record

- Repo: `Porrrrrrg/Formal-Aware-AI-DV-Copilot`
- Local worktree: `D:/AI-DV/Formal-Aware-AI-DV-Copilot`
- Frozen branch: `codex/orchestrator/init-task-graph`
- Base branch: `origin/main`
- Frozen HEAD: `3bb6821e687db39d384abd7f6fcb00cee6f7c6c1`
- GitHub issue freeze notice: issue `#1`, comment id `4416476201`
- This report is the final allowed direct write to the shared worktree. Future edits must be made only on the isolated owner branches below.

## GLOBAL_FREEZE

Shared worktree is frozen. Stop direct writes to the shared overlay. Each subsystem must move its assigned files to the single owner branch listed here, open a draft PR, and wait for the gate checks before merge.

Do not merge until all of these are true:

- canonical IR tests pass
- adapter protocol tests pass
- clean CI passes
- reviewer state changes from `REQUEST_CHANGES` to `MERGE_READY`

## Required command outputs

### `git status --porcelain`

```text
 M .gitignore
 M pyproject.toml
?? .github/
?? Makefile
?? adapters/
?? app/
?? benchmarks/lean_smt_smoke/
?? benchmarks/local_dv/
?? core/
?? docs/agents/
?? docs/architecture/
?? docs/integration/
?? docs/local-llm/
?? docs/research/
?? docs/review/
?? docs/security/
?? ops/
?? reports/
?? schemas/
?? tests/
```

### `git diff --name-status`

```text
M	.gitignore
M	pyproject.toml
warning: in the working copy of '.gitignore', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'pyproject.toml', LF will be replaced by CRLF the next time Git touches it
```

### `git ls-files --others --exclude-standard`

```text
.github/PULL_REQUEST_TEMPLATE.md
.github/workflows/ci.yml
.github/workflows/nightly-bench.yml
.github/workflows/release-attest.yml
Makefile
adapters/__init__.py
adapters/common.py
adapters/lean/__init__.py
adapters/lean/adapter.py
adapters/lean/verify.py
adapters/smt/__init__.py
adapters/smt/common.py
adapters/smt/cvc5/__init__.py
adapters/smt/cvc5/adapter.py
adapters/smt/cvc5/verify.py
adapters/smt/z3/__init__.py
adapters/smt/z3/adapter.py
adapters/smt/z3/verify.py
app/__init__.py
app/core/__init__.py
app/core/artifacts.py
app/core/protocols.py
app/models/__init__.py
app/models/core.py
app/retrieval/__init__.py
app/retrieval/benchmark_registry.py
app/retrieval/evaluate.py
app/retrieval/symbol_index.py
app/retrieval/vector_index.py
benchmarks/lean_smt_smoke/lean/syntax_error.lean
benchmarks/lean_smt_smoke/lean/true.lean
benchmarks/lean_smt_smoke/lean/type_error.lean
benchmarks/lean_smt_smoke/smt/sat.smt2
benchmarks/lean_smt_smoke/smt/syntax_error.smt2
benchmarks/lean_smt_smoke/smt/unsat.smt2
benchmarks/local_dv/README.md
benchmarks/local_dv/registry.json
benchmarks/local_dv/splits/dev.json
benchmarks/local_dv/splits/test.json
benchmarks/local_dv/splits/train.json
benchmarks/local_dv/symbol_index.json
core/__init__.py
core/schemas.py
core/tool_adapter.py
docs/agents/task_graph.md
docs/architecture/typed_ir.md
docs/integration/lean_smt.md
docs/local-llm/qwen_3090ti.md
docs/research/experiment_registry.md
docs/review/review_checklist.md
docs/security/ci_security.md
ops/local-llm/README.md
ops/local-llm/env.example
ops/local-llm/healthcheck.py
ops/local-llm/run_ollama.md
ops/local-llm/run_sglang.sh
ops/local-llm/run_vllm.sh
reports/audits/dependency_inventory_20260510_214819.md
reports/audits/repo_census_20260510_214819.md
reports/audits/repo_tree_20260510_214819.txt
reports/audits/security_surface_20260510_214819.md
reports/eval/local_dv/run_20260510T215354Z/failures.json
reports/eval/local_dv/run_20260510T215354Z/metrics.json
reports/eval/local_dv/run_20260510T215354Z/summary.md
reports/eval/local_dv/run_20260510T215354Z/symbol_index.json
reports/research/ablation_20260510T214913Z.md
reports/research/eval_summary_20260510T214913Z.md
reports/research/risk_register_20260510T214913Z.md
reports/research/runs/20260510T214913Z/coverage_all_systems.json
reports/research/runs/20260510T214913Z/coverage_all_systems_baseline.stderr.txt
reports/research/runs/20260510T214913Z/coverage_all_systems_baseline.stdout.txt
reports/research/runs/20260510T214913Z/prompt_audit.stderr.txt
reports/research/runs/20260510T214913Z/prompt_audit.stdout.txt
reports/research/runs/20260510T214913Z/run_manifest.json
reports/research/runs/20260510T214913Z/sva_generation.json
reports/research/runs/20260510T214913Z/sva_generation_baseline.stderr.txt
reports/research/runs/20260510T214913Z/sva_generation_baseline.stdout.txt
reports/research/runs/20260510T214913Z/sva_repair.json
reports/research/runs/20260510T214913Z/sva_repair_ablation.json
reports/research/runs/20260510T214913Z/sva_repair_baseline.stderr.txt
reports/research/runs/20260510T214913Z/sva_repair_baseline.stdout.txt
reports/research/runs/20260510T214913Z/sva_repair_loop_ablation.stderr.txt
reports/research/runs/20260510T214913Z/sva_repair_loop_ablation.stdout.txt
reports/research/runs/20260510T214913Z/triage_ablation.json
reports/research/runs/20260510T214913Z/triage_all_systems.json
reports/research/runs/20260510T214913Z/triage_all_systems_baseline.stderr.txt
reports/research/runs/20260510T214913Z/triage_all_systems_baseline.stdout.txt
reports/research/runs/20260510T214913Z/triage_structured_ablation.stderr.txt
reports/research/runs/20260510T214913Z/triage_structured_ablation.stdout.txt
reports/review/pr_local_review_20260510T215546Z.md
reports/review/pr_none_review_20260510T214801Z.md
reports/status/orchestrator_status_20260510T214813Z.md
schemas/v1/core.schema.json
tests/adapters/test_cvc5_smoke.py
tests/adapters/test_lean_smoke.py
tests/adapters/test_z3_smoke.py
tests/core/test_schemas.py
tests/retrieval/test_benchmark_registry.py
tests/retrieval/test_evaluate.py
tests/retrieval/test_symbol_index.py
tests/retrieval/test_vector_index.py
tests/test_repo_contracts.py
```

## Owner branches

Every modified or untracked file is assigned to exactly one owner branch. The current report file is included because it is created after the captured command output.

### `owner/core-ir`

Owner: core IR

Files:

- `app/__init__.py`
- `app/core/__init__.py`
- `app/core/artifacts.py`
- `app/core/protocols.py`
- `app/models/__init__.py`
- `app/models/core.py`
- `core/__init__.py`
- `core/schemas.py`
- `docs/architecture/typed_ir.md`
- `schemas/v1/core.schema.json`
- `tests/core/test_schemas.py`

Required gate:

- `python -m pytest tests/core/test_schemas.py`
- Duplicate schema risk `IR-DUP-001` below is resolved or explicitly bridged.

### `owner/lean-smt-adapter-migration`

Owner: Lean/SMT adapter migration

Files:

- `adapters/__init__.py`
- `adapters/common.py`
- `adapters/lean/__init__.py`
- `adapters/lean/adapter.py`
- `adapters/lean/verify.py`
- `adapters/smt/__init__.py`
- `adapters/smt/common.py`
- `adapters/smt/cvc5/__init__.py`
- `adapters/smt/cvc5/adapter.py`
- `adapters/smt/cvc5/verify.py`
- `adapters/smt/z3/__init__.py`
- `adapters/smt/z3/adapter.py`
- `adapters/smt/z3/verify.py`
- `benchmarks/lean_smt_smoke/lean/syntax_error.lean`
- `benchmarks/lean_smt_smoke/lean/true.lean`
- `benchmarks/lean_smt_smoke/lean/type_error.lean`
- `benchmarks/lean_smt_smoke/smt/sat.smt2`
- `benchmarks/lean_smt_smoke/smt/syntax_error.smt2`
- `benchmarks/lean_smt_smoke/smt/unsat.smt2`
- `core/tool_adapter.py`
- `docs/integration/lean_smt.md`
- `tests/adapters/test_cvc5_smoke.py`
- `tests/adapters/test_lean_smoke.py`
- `tests/adapters/test_z3_smoke.py`

Required gate:

- `python -m pytest tests/adapters`
- Adapters import and return the canonical IR selected by `owner/core-ir`.

### `owner/ci-security`

Owner: CI/security

Files:

- `.gitignore`
- `.github/PULL_REQUEST_TEMPLATE.md`
- `.github/workflows/ci.yml`
- `.github/workflows/nightly-bench.yml`
- `.github/workflows/release-attest.yml`
- `Makefile`
- `docs/security/ci_security.md`
- `pyproject.toml`
- `tests/test_repo_contracts.py`

Required gate:

- Clean GitHub Actions CI pass on the final integration candidate.
- Because `pyproject.toml` names packages introduced by other owner branches, this branch merges after the code-owning branches unless it is split by a later approved integration decision.

### `owner/retrieval-benchmark`

Owner: retrieval/benchmark

Files:

- `app/retrieval/__init__.py`
- `app/retrieval/benchmark_registry.py`
- `app/retrieval/evaluate.py`
- `app/retrieval/symbol_index.py`
- `app/retrieval/vector_index.py`
- `benchmarks/local_dv/README.md`
- `benchmarks/local_dv/registry.json`
- `benchmarks/local_dv/splits/dev.json`
- `benchmarks/local_dv/splits/test.json`
- `benchmarks/local_dv/splits/train.json`
- `benchmarks/local_dv/symbol_index.json`
- `tests/retrieval/test_benchmark_registry.py`
- `tests/retrieval/test_evaluate.py`
- `tests/retrieval/test_symbol_index.py`
- `tests/retrieval/test_vector_index.py`

Required gate:

- `python -m pytest tests/retrieval`
- Retrieval fixtures remain deterministic and do not depend on generated report files.

### `owner/local-qwen`

Owner: local Qwen

Files:

- `docs/local-llm/qwen_3090ti.md`
- `ops/local-llm/README.md`
- `ops/local-llm/env.example`
- `ops/local-llm/healthcheck.py`
- `ops/local-llm/run_ollama.md`
- `ops/local-llm/run_sglang.sh`
- `ops/local-llm/run_vllm.sh`

Required gate:

- Shell/doc review only unless CI adds executable checks for local LLM scripts.
- No dependency on CUDA or local model downloads in clean CI.

### `owner/research-eval`

Owner: research/eval

Files:

- `docs/research/experiment_registry.md`
- `reports/eval/local_dv/run_20260510T215354Z/failures.json`
- `reports/eval/local_dv/run_20260510T215354Z/metrics.json`
- `reports/eval/local_dv/run_20260510T215354Z/summary.md`
- `reports/eval/local_dv/run_20260510T215354Z/symbol_index.json`
- `reports/research/ablation_20260510T214913Z.md`
- `reports/research/eval_summary_20260510T214913Z.md`
- `reports/research/risk_register_20260510T214913Z.md`
- `reports/research/runs/20260510T214913Z/coverage_all_systems.json`
- `reports/research/runs/20260510T214913Z/coverage_all_systems_baseline.stderr.txt`
- `reports/research/runs/20260510T214913Z/coverage_all_systems_baseline.stdout.txt`
- `reports/research/runs/20260510T214913Z/prompt_audit.stderr.txt`
- `reports/research/runs/20260510T214913Z/prompt_audit.stdout.txt`
- `reports/research/runs/20260510T214913Z/run_manifest.json`
- `reports/research/runs/20260510T214913Z/sva_generation.json`
- `reports/research/runs/20260510T214913Z/sva_generation_baseline.stderr.txt`
- `reports/research/runs/20260510T214913Z/sva_generation_baseline.stdout.txt`
- `reports/research/runs/20260510T214913Z/sva_repair.json`
- `reports/research/runs/20260510T214913Z/sva_repair_ablation.json`
- `reports/research/runs/20260510T214913Z/sva_repair_baseline.stderr.txt`
- `reports/research/runs/20260510T214913Z/sva_repair_baseline.stdout.txt`
- `reports/research/runs/20260510T214913Z/sva_repair_loop_ablation.stderr.txt`
- `reports/research/runs/20260510T214913Z/sva_repair_loop_ablation.stdout.txt`
- `reports/research/runs/20260510T214913Z/triage_ablation.json`
- `reports/research/runs/20260510T214913Z/triage_all_systems.json`
- `reports/research/runs/20260510T214913Z/triage_all_systems_baseline.stderr.txt`
- `reports/research/runs/20260510T214913Z/triage_all_systems_baseline.stdout.txt`
- `reports/research/runs/20260510T214913Z/triage_structured_ablation.stderr.txt`
- `reports/research/runs/20260510T214913Z/triage_structured_ablation.stdout.txt`

Required gate:

- Eval artifacts are traceable to a run manifest.
- Research outputs do not silently redefine canonical metrics owned by retrieval/benchmark.

### `owner/reports-audits`

Owner: reports/audits

Files:

- `docs/agents/task_graph.md`
- `docs/review/review_checklist.md`
- `reports/audits/dependency_inventory_20260510_214819.md`
- `reports/audits/repo_census_20260510_214819.md`
- `reports/audits/repo_tree_20260510_214819.txt`
- `reports/audits/security_surface_20260510_214819.md`
- `reports/review/pr_local_review_20260510T215546Z.md`
- `reports/review/pr_none_review_20260510T214801Z.md`
- `reports/status/integration_plan_20260510T221015Z.md`
- `reports/status/orchestrator_status_20260510T214813Z.md`

Required gate:

- Report-only PR, no code or workflow changes.
- Final audit PR should be rebased after subsystem PR numbers and statuses are known.

## Merge order

1. `owner/core-ir`: establishes canonical typed IR and resolves or bridges duplicate schema models.
2. `owner/lean-smt-adapter-migration`: depends on canonical IR and owns adapter protocol checks.
3. `owner/retrieval-benchmark`: depends on stable package/import layout and owns benchmark registry tests.
4. `owner/local-qwen`: independent runtime/docs branch; must not require local GPU/model resources in CI.
5. `owner/research-eval`: depends on retrieval/benchmark semantics for local eval artifacts.
6. `owner/ci-security`: lands workflows, packaging config, repo contract checks, and final clean CI after all referenced packages exist.
7. `owner/reports-audits`: final report/audit material, rebased after PR numbers and reviewer states are known.

No branch may merge while reviewer state remains `REQUEST_CHANGES`. Merge readiness must be explicit as `MERGE_READY`.

## Branch isolation procedure

For each owner:

1. Start from `origin/main`.
2. Create the owner branch named above.
3. Add only the exact files listed for that owner.
4. Commit with an owner-scoped message.
5. Push and open a draft PR.
6. Cross-link issue `#1` and this report.
7. Do not stage, commit, or rewrite any path assigned to another owner.

The frozen shared overlay remains a read-only source for extracting assigned files only.

## Blocking risks

### `IR-DUP-001`: duplicate core schema implementations

Status: blocking risk tracked under `owner/core-ir`

Current state:

- `core/schemas.py` defines dataclass-based `ProblemSpec`, `Candidate`, `Diagnostic`, `VerifierOutcome`, and `RunManifest`.
- `app/models/core.py` defines a richer Pydantic-based canonical typed IR with schema generation and validation.
- `core/tool_adapter.py` currently imports adapter contracts from `core.schemas`.

Risk:

- Adapters can pass against the dataclass model while canonical schema tests validate the Pydantic model, creating silent drift between verifier outputs and the JSON Schema.

Required disposition before merge:

- Select `app.models.core` as the canonical IR, or explicitly document and test `core.schemas` as a compatibility facade.
- Adapter protocol tests must prove Lean/Z3/cvc5 outcomes conform to the canonical model.
- The JSON Schema in `schemas/v1/core.schema.json` must be generated from the same canonical implementation that adapters use.

### `CFG-001`: `pyproject.toml` spans multiple owner packages

Status: sequencing risk tracked under `owner/ci-security`

Risk:

- `pyproject.toml` lists packages owned by core, adapters, retrieval, and existing project code. Merging it before the package directories can make clean packaging or CI fail.

Required disposition before merge:

- Merge `owner/ci-security` after the code-owning branches, or make an explicit integration decision to split package metadata in a later plan.

### `EVAL-001`: generated eval artifacts can drift from benchmark definitions

Status: tracked under `owner/research-eval`

Risk:

- `reports/eval` and `reports/research` artifacts can become stale if retrieval benchmark fixtures change before merge.

Required disposition before merge:

- Revalidate or regenerate eval artifacts after `owner/retrieval-benchmark` is merge-ready.

## Acceptance status

- GLOBAL_FREEZE posted: complete.
- Required Git state captured: complete.
- Every modified or untracked file assigned to one owner branch: complete.
- Merge order documented: complete.
- Duplicate `core/schemas.py` vs `app.models.core` risk explicitly tracked: complete.
- Direct shared worktree writes after this report: prohibited.
