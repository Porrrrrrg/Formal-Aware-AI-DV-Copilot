# Repo Cleanup Plan - 2026-05-11T19:33:02Z

Branch: `stage5/repo-hygiene-audit`
Base observed: `origin/main` at `5c3da97ef627fb0df6f52de18760406f847d77eb`
Scope: proposal only. This PR does not delete files, move files, change code
behavior, or edit Qwen reports.

## Principles

- Preserve reproducible source, benchmark, fixture, and sanitized release
  evidence in git.
- Keep raw EDA outputs, local traces, logs, caches, virtual environments,
  generated harness dumps, and machine-specific outputs out of git.
- Treat old coordination/status reports as historical evidence unless an owner
  explicitly declares them superseded.
- Prefer a report index plus retention policy before any file removal.

## Proposed Deletes

Do not delete in this PR. Candidate future deletes after owner approval:

| Candidate | Reason | Precondition |
| --- | --- | --- |
| Tracked local generated stdout/stderr files under `reports/research/runs/**` | They are execution byproducts, not curated summaries. | Add `reports/INDEX.md`, archive or attach exact artifacts to a release, and confirm no test/doc depends on them. |
| Duplicated generated eval snapshots under `reports/eval/local_dv/run_*/**` when equivalent canonical assets exist under `benchmarks/local_dv/` | Avoid storing the same symbol/index payload in both benchmark assets and run output. | Confirm the run snapshot is indexed elsewhere or intentionally preserved. |
| Obsolete blocker/review reports that are superseded by release ledgers | Reduce stale operational guidance. | Mark superseded status in index first; keep at least one archived copy if needed for audit trail. |
| Any future accidental `*.log`, `*.rpt`, `*.jou`, `*.vcd`, `*.fsdb`, `*.wlf`, `traces/`, `jgproject/`, `.venv/`, or `__pycache__/` file | These are already ignored and should remain untracked. | Add/keep contract tests or CI guard before removal PRs. |

## Proposed Archives

Archive means moving to a documented historical namespace or external release
artifact store in a later PR, not deleting in this PR.

| Candidate | Proposed destination | Reason |
| --- | --- | --- |
| `reports/audits/*` from 2026-05-10 | `reports/archive/20260510/audits/` or external release artifacts | Historical baseline audits, mostly superseded by later stage reports. |
| `reports/review/pr_none_*` and `reports/review/pr_local_*` | `reports/archive/20260510/review/` | Pre-integration review state; useful history but stale for current operations. |
| `reports/status/stage3_*`, `reports/status/stage4_*`, older blocker reports | `reports/archive/stage3/` and `reports/archive/stage4/` | Historical gate artifacts should not compete with current status. |
| `reports/research/runs/**` | External artifact bundle referenced from `reports/INDEX.md` | These are generated run payloads and stdout/stderr captures. |
| Large JSONL generated artifacts in `reports/repair/artifacts/*.jsonl` and `reports/alignment/*.jsonl` | Keep if indexed; otherwise archive externally | Useful for reproducibility but less readable than summaries/manifests. |

## Proposed Indexing

Add a follow-up `reports/INDEX.md` and optional `reports/report_registry.json`
with one row per curated report family.

Suggested fields:

- `path`
- `stage`
- `category`
- `created_at_utc`
- `source_branch`
- `base_sha`
- `claim_boundary`
- `summary_path`
- `manifest_path`
- `raw_artifacts_committed`
- `status`: `current`, `historical`, `superseded`, `archive-candidate`
- `owner`

Initial index targets:

- `reports/release/stage3_*` and `reports/release/stage4_*`.
- `reports/workflows/e2e_demo_*` and `reports/workflows/workflow_smoke_*`.
- `reports/alignment/intent_alignment_*`.
- `reports/jasper/*summary*.md` and `reports/jasper/*manifest*.json`.
- `reports/fveval/*`.
- `reports/benchmarks/*`.
- `reports/status/*.md`.
- Generated run groups under `reports/research/runs/**` and
  `reports/eval/local_dv/run_*/**`.

Qwen/local-LLM report indexing should be handled by the owning Qwen/local-LLM
follow-up, since this PR is not touching those reports.

## Proposed Documentation

| Doc task | Reason |
| --- | --- |
| Update `README.md` repository layout to include `app/`, `adapters/`, `core/`, `schemas/`, `ops/`, and `reports/` policy. | Current layout is older than the Stage 5 structure. |
| Consolidate workflow docs between `docs/workflow_usage.md`, `docs/e2e_demo.md`, and `examples/workflows/sva_repair_demo/README.md`. | Avoid drift between command examples and claim boundaries. |
| Add a short report retention policy under `docs/` or `reports/README.md`. | Clarify what belongs in git vs release artifacts. |
| Add a historical-report disclaimer to archived status/review reports. | Prevent old blocker/branch instructions from being mistaken for current state. |
| Document allowed sanitized Jasper artifact shape. | Keep raw `.rpt`, `.log`, trace, and license outputs out of git while preserving usable proof summaries. |

## Proposed Test/CI Protections

| Protection | Target |
| --- | --- |
| Extend `tests/test_repo_contracts.py` with a tracked-file denylist for raw EDA outputs: `*.log`, `*.rpt`, `*.jou`, `*.vcd`, `*.fsdb`, `*.wlf`, `traces/`, `jgproject/`. | Prevent accidental raw Jasper/EDA artifacts from entering git. |
| Add a tracked-file denylist for cache/env paths: `__pycache__/`, `.pytest_cache/`, `.ruff_cache/`, `.mypy_cache/`, `.venv/`, `venv/`, `env/`, `.env`. | Keep local-only generated files out of source control. |
| Add a max-size or allowlist check for tracked files above a threshold such as 1 MB. | Catch large generated artifacts early. |
| Add a reports index consistency test once `reports/INDEX.md` or `reports/report_registry.json` exists. | Ensure new report families are discoverable and marked current/historical. |
| Add a sanitized-report contract for Jasper workflow imports. | Ensure future workflow demos continue to reject raw logs/traces. |

## Proposed Sequence

1. Create `reports/INDEX.md` and classify existing reports as current,
   historical, superseded, or archive-candidate.
2. Add tracked-file hygiene tests for raw EDA outputs, caches, virtualenvs,
   local env files, and large artifacts.
3. Update docs with the report retention policy and refreshed repository layout.
4. Archive historical status/review/audit reports in a dedicated follow-up PR,
   after owners agree on the destination.
5. Move or externalize generated run payloads only after the index points to a
   durable artifact location.

## Non-Actions In This PR

- No deletes.
- No archive moves.
- No edits to Qwen reports.
- No code behavior changes.
- No report index creation beyond this cleanup proposal.
