# Stage 3 Gate Kickoff

Timestamp: 2026-05-11T03:07:46Z

Tracking issue: Porrrrrrg/Formal-Aware-AI-DV-Copilot#23

Base observed locally: `origin/main` at `ff45f9f8c6cc7102d26d04665640ed4fb6cb7f9e`

Gate branch observed locally: `stage/stage3-gate-report` at `ff45f9f8c6cc7102d26d04665640ed4fb6cb7f9e`

## Local Stage 3 Setup

Observed local worktrees:

- `stage/stage3-gate-report`: clean, based on `origin/main`.
- `stage/sva-repair-failure-analysis`: clean, based on `origin/main`.
- `stage/benchmark-expansion-fifo-vacuity`: based on `origin/main`; contains untracked `.tmp_fveval_source/`.
- `stage/fveval-subset-integration`: clean, based on `origin/main`.

Branches named in issue #23 but not observed as local worktrees during kickoff:

- `stage/cex-aware-repair-loop`
- `stage/codex-repair-jasper-validation`

No remote `origin/stage/*` refs were observed for the Stage 3 branches after `git fetch origin --prune`.

## Merge Order

Stage 3 PRs should be reviewed and sequenced in this order:

1. `stage/sva-repair-failure-analysis`
2. `stage/cex-aware-repair-loop`
3. `stage/codex-repair-jasper-validation`
4. `stage/benchmark-expansion-fifo-vacuity`
5. `stage/fveval-subset-integration`

Gate policy: later PRs should be reviewed against the merged result of earlier Stage 3 PRs. If PRs are opened in parallel, treat the merge order above as the integration sequence and request rebase or retest when a prior PR changes shared behavior, benchmark data, reports, schemas, or evaluation assumptions.

## Protected Paths And Claims Policy

The gate will block or request revision for:

- Schema changes unless explicitly scoped in the PR and tracking issue.
- Benchmark label modifications unless accompanied by an explicit report explaining the change.
- Raw Jasper logs committed to the repository.
- Cloud prompt export without explicit acknowledgement.
- Ambiguous production-readiness, signoff automation, Qwen quality, or Qwen-vs-Codex claims.

## Required PR Evidence

Every future Stage 3 PR must include:

- Git SHA reviewed.
- Commands run.
- Test results.
- Whether Jasper was used.
- Whether Codex was used.
- Whether Qwen was used.
- Whether each result is scaffold, formal, or real LLM output.

## Initial Gate Checklist

- Confirm PR branch and base SHA.
- Confirm PR follows the Stage 3 merge order, or document why it is being reviewed out of order.
- Check protected paths and claims policy.
- Check benchmark labels and require a report for any label edits.
- Check for raw Jasper logs or other unintended generated artifacts.
- Check cloud prompt export acknowledgement when applicable.
- Verify commands and test results are present and reproducible enough for the claimed scope.
- Classify evidence as scaffold, formal, or real LLM before accepting claims.
- Require rebase/retest when prior Stage 3 PRs land first.

