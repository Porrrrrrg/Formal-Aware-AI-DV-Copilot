# Dependency Inventory

- Repository: `Porrrrrrg/Formal-Aware-AI-DV-Copilot`
- HEAD: `3bb6821e687db39d384abd7f6fcb00cee6f7c6c1`
- UTC: `2026-05-10 21:48:19`
- Evidence commands: `git ls-files`, `rg --files`, `rg -n "^(import|from) "`, local Python smoke commands.
- Scope note: base inventory is audited tracked HEAD. A local worktree overlay appeared during verification and is recorded separately because it is modified/untracked relative to audited HEAD.

## Package Manifests

| File | Evidence | Finding |
| --- | --- | --- |
| `pyproject.toml` | `[project]`, `requires-python = ">=3.10"`, `dependencies = []` | Python package metadata exists but declares no runtime dependencies. |
| `requirements*.txt` | Not found by manifest scan | Unspecified. |
| `setup.py` / `setup.cfg` | Not found by manifest scan | Unspecified. |
| `package.json` / JS lockfiles | Not found by manifest scan | No Node package evidence. |
| `Dockerfile*` / `docker-compose*.yml` | Not found by manifest scan | No Docker evidence. |
| `lakefile.*` / `lean-toolchain` | Not found by manifest scan | No Lake/Lean project evidence. |

## Worktree Overlay Manifests

Current local `pyproject.toml` is modified relative to HEAD. Observed overlay additions:

- Runtime dependencies: `jsonschema>=4.22,<5`, `pydantic>=2.7,<3`.
- Optional dev dependency: `pytest>=8,<9`.
- Build system: `setuptools>=68`.
- Package list includes `app`, `app.core`, `app.models`, `copilot`, `copilot.agents`, `copilot.baselines`, `tools`.
- `Makefile` targets: `test`, `retrieval-registry`, `retrieval-index`, `retrieval-eval`, `nightly-bench`.
- Optional vector dependency is not declared: `app/retrieval/vector_index.py` imports `qdrant_client` only when Qdrant env config is present.

## Python Runtime

- Declared Python: `>=3.10` in `pyproject.toml`.
- Local audit interpreter: `Python 3.11.9`.
- Tracked HEAD `pytest --collect-only` could not run because local `pytest` was not installed and tracked `tests/` was not found at that point.
- Worktree overlay `pytest --collect-only` passed and collected tests under `tests`.
- Worktree overlay `python -m pytest` passed: 52 tests.
- `pyproject.toml` contains `[tool.pytest.ini_options] testpaths = ["tests"]`.
- `ruff` settings exist in `pyproject.toml`; `ruff` is not declared as a dependency.

## Python Imports

Observed imports are mostly standard library plus local packages:

- Standard library: `argparse`, `collections`, `copy`, `dataclasses`, `gzip`, `hashlib`, `json`, `os`, `pathlib`, `re`, `shutil`, `subprocess`, `sys`, `tempfile`, `typing`.
- Local packages: `copilot.*`, `evaluation.*`, `scripts.*`, `tools.*`.
- Optional external dependency: `jsonschema` in `tools/validate_json.py`; code falls back to required-key validation if missing.
- Worktree overlay external dependency: `pydantic` in `app/models/core.py` and `app/core/artifacts.py`.
- Worktree overlay optional external dependency: `qdrant_client` in `app/retrieval/vector_index.py`, not required unless Qdrant config is provided.

Tracked HEAD had no evidence for pinned third-party Python dependency versions. Worktree overlay adds version ranges but no lockfile.

## External Tools and Services

| Tool/service | Evidence path | Use |
| --- | --- | --- |
| JasperGold `jg` | `tools/run_jasper.py`, `tools/check_generated_sva.py`, `benchmarks/*/formal/run_jg.tcl`, `jasper/common/*.tcl` | Formal prove/cover/vacuity execution and generated SVA re-check. |
| Cadence env on `moore` | `README.md`, `scripts/run_moore_*.sh`, `docs/moore_smoke_results.md` | Expected setup: `source /vol/eecs391/cadence.env`, `JASPER_BIN=/vol/cadence2018/XCELIUM1809/tools.lnx86/jasper/bin/jg`, `python3.11`. |
| Codex CLI | `copilot/llm_adapters/codex_json.py`, `scripts/run_codex_llm_eval.py`, `docs/codex_cli_usage.md` | Optional non-interactive LLM backend, guarded by explicit benchmark export acknowledgement in the wrapper. |
| Bash | `scripts/run_moore_smoke.sh`, `scripts/run_moore_sva_eval.sh`, `scripts/run_moore_sva_repair_eval.sh` | Moore convenience scripts. |

## Formal and DV Assets

- SystemVerilog RTL/formal files: 21 tracked `.sv` files.
- Jasper TCL files: 8 tracked `.tcl` files.
- Benchmarks: `arbiter_rr2`, `rv_buffer`, `apb_regblock`.
- Per design: 10 labeled cases, 4 RTL variants, 4 formal files, 3 manifests.
- SVA generation dataset: `benchmarks/sva_generation_cases.json` has 27 cases.
- SVA repair dataset: `benchmarks/sva_repair_cases.json` has 18 cases.
- Triage/coverage labeled cases: 30 cases across three designs.

## Verification Commands Run During Audit

| Command | Result |
| --- | --- |
| `python evaluation/run_eval.py --cases benchmarks/arbiter_rr2/cases benchmarks/rv_buffer/cases benchmarks/apb_regblock/cases` | Passed; 30 cases summarized, oracle scaffold accuracy 1.0. |
| `python evaluation/run_agent_eval.py --limit 3` | Passed; structured fallback on 3 cases, issue/action accuracy 1.0. |
| `python evaluation/run_sva_eval.py --limit 3` | Passed; direct and structured scaffold results emitted. |
| `python evaluation/run_sva_repair_eval.py --limit 3 --max-rounds 1` | Passed; structured fallback repair success 1.0 on sampled cases. |
| `python evaluation/run_coverage_eval.py --limit 3` | Passed; structured fallback coverage action accuracy 1.0 on sampled cases. |
| `python scripts/export_codex_prompts.py --task all --limit 3 --summary-only` | Passed; 9 prompts, 0 with gold labels, 9 with Jasper evidence markers. |
| Tracked HEAD `python -m pytest --collect-only` | Blocked locally; `pytest` not installed and no tracked `tests/` directory found. |
| Worktree overlay `python -m pytest --collect-only` | Passed; collected tests under `tests/`. |
| Worktree overlay `python -m pytest` | Passed; 52 tests. |

## Dependency Risks

- P1: Tracked HEAD has no CI or test dependency contract. Evidence: `.github/` and `tests/` absent from `git ls-files` at audited HEAD. Worktree overlay appears to mitigate but is uncommitted.
- P1: Formal execution is environment-specific. Evidence: `scripts/run_moore_*.sh` hard-code a default Jasper path under `/vol/cadence2018/...`; Docker was not found.
- P2: Validation quality depends on optional `jsonschema`. Evidence: `tools/validate_json.py` uses a top-level required-key fallback when `jsonschema` is absent.
- P2: No dependency lockfiles or pinned tool versions were found. Evidence: tracked HEAD manifest scan found only `pyproject.toml` with `dependencies = []`; worktree overlay uses version ranges but no lockfile.
