# CI/CD Security Model

This repository uses GitHub Actions for low-risk, deterministic checks and keeps
Cadence/JasperGold work off the default hosted runners. The default posture is
no long-lived cloud secrets, no external LLM calls, and least-privilege workflow
tokens.

## Workflows

- `.github/workflows/ci.yml`
  - Runs on pull requests, pushes to `main`, and manual dispatch.
  - Gates PRs with workflow lint, Ruff, pytest, schema validation, deterministic
    smoke tests, secret scanning, CodeQL, and a human review check.
  - Attests CI smoke artifacts on trusted non-PR events only.
- `.github/workflows/nightly-bench.yml`
  - Runs nightly and on manual dispatch.
  - Builds local evidence packets, runs deterministic benchmark entrypoints, writes
    `summary.md`, uploads artifacts, and creates artifact attestations.
- `.github/workflows/release-attest.yml`
  - Runs on published releases and manual dispatch.
  - Re-runs release validation, packages the repository with `git archive`, writes
    SHA-256 metadata, uploads artifacts, and creates provenance attestations.

## Required Branch Protection

Configure `main` in GitHub branch protection or repository rulesets:

- Require a pull request before merging.
- Require at least one approving review from a non-bot reviewer.
- Dismiss stale approvals when new commits are pushed.
- Block direct pushes to `main`; only admins may bypass in emergencies.
- Require these status checks before merge:
  - `Review gate`
  - `Workflow lint`
  - `Python lint and tests`
  - `Schema validation`
  - `Secret scan`
  - `Adapter and benchmark smoke`
  - `CodeQL`
- Require branches to be up to date before merging when practical.

The `Review gate` workflow check is a CI-side backstop. Branch protection is
still the source of truth for preventing direct pushes and merges without review.

## Token Permissions

Workflow permissions are explicit. Most jobs get `contents: read` only. Jobs that
upload SARIF get `security-events: write`. Attestation jobs get only:

- `contents: read`
- `id-token: write`
- `attestations: write`

Do not add long-lived cloud credentials or personal tokens to repository secrets.
If a future deployment needs cloud access, use GitHub OIDC with provider-side
audience, repository, ref, and environment conditions.

## Network Policy

Default CI jobs should only contact:

- GitHub Actions service endpoints for checkout, artifacts, CodeQL, and
  attestations.
- GitHub-hosted action sources referenced in the workflow.
- PyPI for declared project dependencies and CI-only Python tools such as
  `ruff`, `pytest`, and `jsonschema`.

Do not configure `JASPERLOOP_LLM_CMD`, hosted LLM API keys, or external prompt
submission in default CI. Benchmark content may be sent externally only through
an explicit, reviewed workflow that documents data exposure and requires a manual
approval gate.

## Offline Runner Strategy

Full JasperGold validation belongs on `moore` or another isolated self-hosted
runner, not on GitHub-hosted runners. The expected lab setup is:

```bash
ssh moore
source /vol/eecs391/cadence.env
```

Recommended runner controls:

- Use a dedicated runner label such as `self-hosted`, `linux`, `moore`, `offline`.
- Keep egress blocked except for the minimum GitHub runner control plane traffic,
  or use a pre-synced mirror/worktree if the runner is fully offline.
- Do not place cloud credentials or hosted LLM credentials on the runner.
- Source `/vol/eecs391/cadence.env` inside the job or runner wrapper.
- Set `JASPER_BIN` to the local JasperGold binary when needed.
- Upload only parsed reports, summaries, and redacted artifacts required for
  review. Do not upload license files, home directories, caches, or raw secrets.

The committed workflows intentionally run Jasper dry-runs or deterministic
scaffold checks by default. A future Jasper self-hosted workflow should be manual
dispatch only until the lab runner isolation is reviewed.

## Attestation Verification

Release and benchmark artifacts are attested through GitHub artifact attestations.
After downloading an artifact, verify provenance with GitHub CLI:

```bash
gh attestation verify <artifact-file> --repo Porrrrrrg/Formal-Aware-AI-DV-Copilot
```

For release bundles, also compare the downloaded archive hash with the matching
`.sha256` file.

## Labels

Use labels to make review ownership explicit:

- `ci`: workflows, test gates, actionlint, branch protection.
- `security`: token permissions, secret scanning, CodeQL, attestations.
- `schema`: JSON schemas, validators, evidence packet shape.
- `benchmark`: evaluation entrypoints or result artifacts.
- `jasper`: Cadence/JasperGold runner behavior.
- `needs-moore`: requires validation on the lab server.
- `external-llm`: may send benchmark prompts or outputs outside the repo.
- `docs`: documentation-only changes.

Changes labeled `security`, `external-llm`, or `needs-moore` should get explicit
review from the CI/CD and DV owners before merge.

## Branch Naming

Use short, scoped branch names:

- `ci/<short-task>` for workflow and test gate changes.
- `security/<short-task>` for security controls and attestation changes.
- `bench/<short-task>` for benchmark and nightly result changes.
- `schema/<short-task>` for JSON schema changes.
- `docs/<short-task>` for documentation-only work.
- `codex/<agent-role>/<short-task>` for multi-agent implementation branches.

Avoid branch names that include secrets, ticket contents, customer names, or
private lab paths.
