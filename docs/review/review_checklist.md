# PR Review Checklist

This checklist is the merge gate for JasperLoop-DV PRs. A PR is not
`MERGE_READY` until every required item is marked `PASS` with file-backed
evidence, or explicitly scoped out with a reviewer-approved reason.

## Required PR Metadata

Every PR must declare:

- `subsystem`: one of `core`, `adapters`, `benchmarks`, `evaluation`, `jasper`, `llm`, `security`, `github-automation`, or `docs`.
- `owner`: the responsible agent or human reviewer.
- `issue`: the linked issue or task id.
- `run_id`: the replayable run or `N/A` for docs-only changes.
- `benchmark impacted`: `yes` or `no`; if `yes`, name the split.

Naming gates:

- Branch: `codex/<agent>/<issue-id>-<slug>`
- Commit: `type(scope): summary [issue #123]`
- PR title: `[codex][<agent>] <summary>`

## Checklist

| Area | Required checks | Status |
| --- | --- | --- |
| Modularity | New logic lives in the correct subsystem and is not coupled into CLI scripts unless the PR is explicitly CLI-only. | PASS / FAIL / NEEDS EVIDENCE |
| Typed IR | JSON Schema, Python models, and API input/output names agree. `RunManifest`, `ProblemSpec`, `Candidate`, `VerifierOutcome`, and artifact references are covered when touched. | PASS / FAIL / NEEDS EVIDENCE |
| Adapter API | Formal tool adapters expose consistent `build`, `run`, and `verify` boundaries, while preserving tool-specific diagnostics. | PASS / FAIL / NEEDS EVIDENCE |
| Tests | The PR includes focused unit tests, smoke coverage, and failure-path tests for the changed subsystem. | PASS / FAIL / NEEDS EVIDENCE |
| Reproducibility | Runs write or update replayable manifests with git SHA, tool versions, command, input refs, output refs, and random seed when relevant. | PASS / FAIL / NEEDS EVIDENCE |
| Security | No hard-coded secrets, unsafe shell expansion, unexpected network egress, or privilege expansion. External LLM export remains explicit opt-in. | PASS / FAIL / NEEDS EVIDENCE |
| GitHub Automation | Workflow triggers, permissions, labels, branch rules, CodeQL, secret scanning, OIDC, and artifact attestation are not weakened. | PASS / FAIL / NEEDS EVIDENCE |
| Benchmark Integrity | Benchmark PRs preserve train/dev/test boundaries, record provenance, and include a leakage check or explicit split audit. | PASS / FAIL / NEEDS EVIDENCE |

## Required Evidence Commands

Run the commands that apply to the changed subsystem and paste the exact result
or artifact path in the PR:

```bash
python -m compileall copilot tools evaluation scripts
python -m pytest
python evaluation/run_eval.py --cases benchmarks/arbiter_rr2/cases benchmarks/rv_buffer/cases benchmarks/apb_regblock/cases
python evaluation/run_agent_eval.py --all-systems --out evaluation/results/agent_eval_local.json
python evaluation/run_sva_repair_eval.py --out evaluation/results/sva_repair_local.json
python evaluation/run_coverage_eval.py --all-systems --out evaluation/results/coverage_eval_local.json
```

Schema checks must include every touched schema and representative payload:

```bash
python tools/validate_json.py copilot/schemas/evidence_packet.schema.json <evidence_packet.json>
```

JasperGold smoke must run on `moore` for PRs touching `jasper`, formal flows,
RTL benchmarks, SVA generation, SVA repair, coverage closure, or Jasper parsers:

```bash
ssh moore
cd /path/to/Formal-Aware-AI-DV-Copilot
source /vol/eecs391/cadence.env
bash scripts/run_moore_smoke.sh
```

Workflow PRs must also run `actionlint` when available and must explain any
permission changes.

## Automatic Blockers

Request changes immediately when any of these are true:

- A secret, token, credential, private key, or machine-specific credential path is added.
- A PR changes `.github/workflows/**` and removes or weakens least-privilege permissions, OIDC intent, CodeQL coverage, secret scanning expectations, or artifact attestation.
- A benchmark PR changes or adds cases without documenting provenance and split placement.
- A typed IR or adapter PR changes field names without updating schemas, models, tests, and replay artifacts together.
- The PR omits subsystem owner metadata.
- The PR targets `main` directly or bypasses the `codex/<agent>/<issue-id>-<slug>` branch convention without an approved exception.

## Merge Gate Labels

Use these labels consistently:

- `review/pass`
- `review/request-changes`
- `blocked/ci`
- `blocked/schema`
- `blocked/security`
- `blocked/reproducibility`
- `needs-owner`
- `needs-benchmark-split-audit`
- `MERGE_READY`

Only apply `MERGE_READY` after CI is green, every checklist item is `PASS`, and
the review summary artifact has been committed or linked from the PR.
