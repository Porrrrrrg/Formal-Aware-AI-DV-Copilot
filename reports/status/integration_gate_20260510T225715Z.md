# Integration Gate 20260510T225715Z

UTC update: 2026-05-11T00:10:37Z

Scope: PRs #10-#16 for the JasperLoop-DV owner staging queue. This report is preserved as the integration gate record and updated by the final reports/audits PR after #12, #10, #11, #13, #14, and #15 were merged.

No real Codex, Qwen, cloud, JasperGold, or proprietary benchmark run was executed during this merge sequence. The only regenerated benchmark artifact was the deterministic local retrieval report for #15, using the local sparse index and canonical `VerifierOutcome` output.

## Applied Merge Order

1. #12 `owner/ci-security`
2. #10 `owner/core-ir`
3. #11 `owner/lean-smt-adapter-migration`
4. #13 `owner/retrieval-benchmark`
5. #14 `owner/local-qwen`
6. #15 `owner/research-eval`
7. #16 `owner/reports-audits`

## Branch Protection

Main branch protection was enabled after #12 merged.

- Pull request before merge: enabled.
- Required status checks: enabled with strict up-to-date branches.
- Required contexts: `Review gate`, `Workflow lint`, `Python lint and tests`, `tests/core`, `tests/adapters`, `tests/retrieval`, `tests/test_repo_contracts.py`, `schemas/v1/core.schema.json`, `Schema validation`, `Secret scan`, `Adapter and benchmark smoke`, `CodeQL`.
- Conversation resolution: required.
- Force pushes: blocked.
- Branch deletions: blocked.
- Approving reviews: not required because this is operating as a solo repository; the review gate accepts non-draft PRs with no `CHANGES_REQUESTED` review and the maintainer-controlled `MERGE_READY` label.

## Tests And Gates

| PR | Branch | Local checks | CI result | Review gate |
|---:|---|---|---|---|
| #12 | `owner/ci-security` | `python -m ruff check .`; `python -m pytest -q` passed, 32 tests. | CI run `25643115468` succeeded. | Ready-for-review, `MERGE_READY`, no requested changes. |
| #10 | `owner/core-ir` | `python -m pytest tests/core -q` passed, 11 tests; `python -m pytest -q` passed, 43 tests. | CI run `25643191615` succeeded. | Ready-for-review, `MERGE_READY`, no requested changes. |
| #11 | `owner/lean-smt-adapter-migration` | No forbidden `core.schemas` imports; `python -m pytest tests/adapters -q` passed, 13 tests; `python -m pytest -q` passed, 56 tests. | CI run `25643265037` succeeded. | Ready-for-review, `MERGE_READY`, no requested changes. |
| #13 | `owner/retrieval-benchmark` | Canonical `VerifierOutcome` and `schema_drift` verified; `python -m pytest tests/retrieval -q` passed, 7 tests; `python -m pytest -q` passed, 63 tests. | CI run `25643315464` succeeded. | Ready-for-review, `MERGE_READY`, no requested changes. |
| #14 | `owner/local-qwen` | Scope scan stayed under local runtime/docs/tests/reports; no real Qwen benchmark; `python -m pytest tests/test_local_qwen_healthcheck.py -q` passed, 2 tests; `python -m pytest -q` passed, 65 tests. | CI run `25643382904` succeeded. | Ready-for-review, `MERGE_READY`, no requested changes. |
| #15 | `owner/research-eval` | Deterministic retrieval report revalidated after #13; `python -m pytest tests/retrieval -q` passed, 7 tests; `python -m pytest -q` passed, 65 tests; `python -m ruff check .` passed. | CI run `25643543309` succeeded. | Ready-for-review, `MERGE_READY`, no requested changes. |
| #16 | `owner/reports-audits` | Report-only scope confirmed; `git diff --check` passed; `python -m pytest -q` passed, 65 tests; `python -m ruff check .` passed. | Pending final CI. | Pending ready-for-review and `MERGE_READY`. |

## PR Gate Table

| PR | Branch | Final action at this update | Merge commit or blocker | Branch deletion |
|---:|---|---|---|---|
| #12 | `owner/ci-security` | Merged first after solo-repo review gate patch. | `61bd60a386c6173638cc9d9e59d2f3fe5b99018f` | Remote branch deleted after merge. |
| #10 | `owner/core-ir` | Rebased after #12, then merged. | `3788216d93c466dc2a1324036475b4324166816e` | Remote branch deleted after merge. |
| #11 | `owner/lean-smt-adapter-migration` | Rebased after #10, adapter docs aligned, then merged. | `082c43483036a5f7d6381b8aac8d85163050e59b` | Remote branch deleted after merge. |
| #13 | `owner/retrieval-benchmark` | Rebased after #11, canonical retrieval artifacts verified, then merged. | `9dc6604f6adcb5e2597ef607d16b3182df880736` | Remote branch deleted after merge. |
| #14 | `owner/local-qwen` | Rebased after #13, local-healthcheck scope clarified, then merged. | `6116e932ed12a7f50a5b161970b19afa9b1bd378` | Remote branch deleted after merge. |
| #15 | `owner/research-eval` | Rebased after #14, deterministic eval artifacts revalidated, then merged. | `c51a82c2c7c95b98e882b7c71ebe522f5eb7040c` | Remote branch deleted after merge. |
| #16 | `owner/reports-audits` | Rebased after #15; final report-only update in progress. | Pending final CI and merge. | Delete only after merge. |

## Scope Notes

- #12 was confirmed to contain CI/security/package/test-contract changes plus the solo-repo review gate patch. No core logic changes were added.
- #10 established the canonical core IR before adapter migration.
- #11 had no remaining `from core.schemas` or `import core.schemas` imports after rebase and documentation cleanup.
- #13 owns retrieval benchmark semantics and emits canonical `ProblemSpec`, `Candidate`, `VerifierOutcome`, and `schema_drift` artifacts.
- #14 is limited to local Qwen runtime manifests and healthcheck scaffolding. No Qwen benchmark or cloud comparison was run.
- #15 is scaffold baseline evidence only. It does not claim real LLM, Qwen, cloud, or JasperGold performance.
- #16 remains report-only and must merge last.

## Remaining Work

- Convert #16 from draft to ready-for-review.
- Apply `MERGE_READY` only after report-only scope and local checks pass.
- Merge #16 only after final CI is green.
- Delete `owner/reports-audits` only after #16 merges.
