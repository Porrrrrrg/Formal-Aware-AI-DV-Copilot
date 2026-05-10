# Integration Gate 20260510T225715Z

UTC timestamp: 2026-05-10T22:57:15Z

Scope: PRs #10-#16 for the JasperLoop-DV owner staging queue. No branches were merged, closed, deleted, or newly created. No real Codex, Qwen, JasperGold, or benchmark run was executed.

## Merge Order

1. #10 `owner/core-ir`
2. #11 `owner/lean-smt-adapter-migration`
3. #12 `owner/ci-security`
4. #13 `owner/retrieval-benchmark`
5. #14 `owner/local-qwen`
6. #15 `owner/research-eval`
7. #16 `owner/reports-audits`

## Tests Run

Local integrated workspace:
- `python -m pytest -q` - passed, 65 tests.
- `python -m pytest tests/core -q` - passed, 11 tests.
- `python -m pytest tests/adapters -q` - passed, 13 tests.
- `python -m pytest tests/retrieval -q` - passed, 7 tests.
- `python -m ruff check .` - passed.

Branch-local checks:
- #10 `python -m pytest tests/core -q` - passed, 11 tests.
- #12 `python -m pip install -e ".[dev]"` - passed.
- #12 `python -m pytest tests/test_repo_contracts.py -q` - passed, 32 tests.
- #12 `python -m ruff check .` - passed.
- #14 `python -m pytest tests/test_local_qwen_healthcheck.py -q` - passed, 2 tests.

GitHub Actions:
- #12 latest run `25642052699` on `a5bd60db9ea4a494ed8aa8aa01b41e7e0acd4640` completed with overall failure only because `Review gate` rejects draft PRs.
- Non-review CI jobs in that run passed: Workflow lint, Python lint and tests, tests/core, tests/adapters, tests/retrieval, tests/test_repo_contracts.py, schema validation, core schema parity, secret scan, CodeQL, and adapter/benchmark smoke.

## PR Gate Table

| PR | Branch | Head | Status | CI result | Blockers | Delete branch after merge |
|---:|---|---|---|---|---|---|
| #10 | `owner/core-ir` | `aa0a941de387ac83faf92e0b55293677a1b062c8` | Open draft; mergeable. Canonical `app.models.core` and `schemas/v1/core.schema.json` present; `core/schemas.py` removed. | No individual CI run after #12; local core gate passed. | Await clean final CI and MERGE_READY review. | Yes, after merge and downstream references are no longer needed. |
| #11 | `owner/lean-smt-adapter-migration` | `85bbe866a54246334571f7788d2e41c2a4388a4a` | Open draft; mergeable. Runtime/tests import canonical `app.models.core` and `app.core.protocols`; no `core.schemas` imports found. | No individual CI run after #12; integrated adapter gate passed. | Depends on #10; await clean final CI and MERGE_READY review. | Yes, after merge. |
| #12 | `owner/ci-security` | `a5bd60db9ea4a494ed8aa8aa01b41e7e0acd4640` | Open draft; mergeable. Clean install blocker fixed with dynamic package discovery and `python -m pip install -e ".[dev]"`. | Overall failed due draft Review gate only; all non-review CI jobs passed. | Draft review gate and MERGE_READY review. | Yes, after merge. |
| #13 | `owner/retrieval-benchmark` | `c7c03e939ff1aaa6927c685ea599184f8f91dc4d` | Open draft; mergeable. Retrieval reports now emit canonical `VerifierOutcome` artifacts. | No individual CI run after #12; integrated retrieval gate passed. | Depends on #10 and #12; await clean final CI and MERGE_READY review. | Yes, after merge. |
| #14 | `owner/local-qwen` | `9ec2edefd6017e8343bcf6793126b6253c132faa` | Open draft; mergeable. Scope limited to `ops/local-llm/**`, `docs/local-llm/**`, `tests/test_local_qwen_healthcheck.py`, and `reports/local_llm/**`. | No individual CI run after #12; branch-local healthcheck test passed. | Await clean final CI and MERGE_READY review. | Yes, after merge. |
| #15 | `owner/research-eval` | `4242fab646b702274cb5419a8a0489b1a3273f37` | Open draft; mergeable. Report artifacts label deterministic scaffold results and do not claim real LLM/Qwen/Jasper performance. | No new CI run. | Revalidate after #13 is final; await clean final CI and MERGE_READY review. | Yes, after merge. |
| #16 | `owner/reports-audits` | this report commit | Open draft; report-only. | No new CI run yet for this report commit. | Await this report push, clean final CI, and MERGE_READY review. | Yes, after merge. |

## Changes Pushed

- #10: pushed `aa0a941` to remove legacy `core/schemas.py`, keep top-level `core` as compatibility exports, regenerate the core schema, and add a boundary test.
- #11: pushed `85bbe86` to migrate Lean/SMT adapters and tests to canonical IR/protocol imports.
- #12: pushed `a5bd60d` to fix editable installs in clean CI, add conditional focused CI gates, and avoid retrieval Makefile failures before #13 lands.
- #13: pushed `c7c03e9` to write canonical retrieval `problem_spec.json`, `candidate.json`, and `verifier_outcome.json`.
- #14: pushed `9ec2ede` to add local Qwen healthcheck manifest fields, local-only tests, and local health reports.
- #15: no code changes made.
- #16: this report is the only new report/audit change.

## Blockers

- All PRs remain draft; no PR was converted to ready-for-review.
- GitHub review state is not MERGE_READY. Connector review lookup returned no submitted reviews on #10-#16.
- #12 CI is not clean overall because the review gate fails draft PRs; all non-review CI jobs are green.
- `gh` CLI is not installed in this environment, so CI inspection used the GitHub connector rather than `gh`.
- Main branch protection still needs to be enabled after #12 CI is green with: Require pull request before merging, Require status checks to pass, Require branches to be up to date, Require conversation resolution, Block force pushes, Block deletions.
