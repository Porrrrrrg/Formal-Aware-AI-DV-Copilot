# Stage 3 Release Checkpoint

Created UTC: 20260511T062042Z

Checkpoint commit: `a13eeeca64817f8257c22c7c4aaacb21527241f6`

Planned tag: `stage3-checkpoint-a13eeec`

## Scope

This checkpoint freezes the Stage 3 baseline after the Moore/JasperGold evidence
work, real Codex benchmark reports, Codex repair final-proof validation, benchmark
expansion, FVEval-compatible subset import, and Stage 3 closeout reports were
merged to `main`.

This is a report-only checkpoint. It does not change code behavior, rerun
benchmarks, update schemas, call models, run Qwen, or claim production readiness.

## Baseline State

- Typed IR, canonical schemas, and adapter protocol are stable on `main`.
- Stage 2A Moore/JasperGold evidence packet validation is recorded.
- Stage 2D full Codex benchmark is recorded.
- Stage 3D Codex repair final Jasper proof validation is recorded.
- FIFO/vacuity benchmark expansion is merged with metadata-only evidence boundary.
- FVEval-compatible subset integration is merged with non-reproduction limitations.
- Qwen remains a readiness blocker; no Qwen subset or quality claim is supported.
- Open PR queue was empty before this checkpoint branch was created.

## Verification

Run on `stage/stage3-release-checkpoint` at `a13eeeca64817f8257c22c7c4aaacb21527241f6`:

| Command | Result |
| --- | --- |
| `python -m pytest -q` | 264 passed |
| `python -m ruff check .` | All checks passed |
| `git diff --check` | Passed |

## Claim Boundary

- Stage 3D final-proof results are live Moore/JasperGold outcomes for restored
  Codex repair candidates, not a production signoff automation claim.
- Case-level best-of-candidates pass@k remains an upper-bound search result, not
  single-output repair success.
- `non_vacuous_proven` means proven and not parsed as vacuous in the manifest;
  it is not an independent explicit non-vacuity certificate.
- FIFO/vacuity expansion is benchmark metadata only until live Moore evidence is
  generated for the new cases.
- FVEval-compatible import is not an official FVEval reproduction and does not
  reproduce commercial property-equivalence scoring.
- Qwen local quality, latency, cost, and Qwen-vs-Codex comparisons remain
  unsupported.

## Stage 4 Entry Criteria

Future Stage 4 work should start from this tag and preserve the checkpoint's
claim boundaries. The next experiments should be narrow, manifest-backed, and
separate scaffold, LLM, and formal evidence:

1. SVA repair ablation with selected-output and best-of-k metrics separated.
2. Moore evidence generation for the expanded FIFO/vacuity benchmark cases.
3. FVEval-compatible subset evaluation without answer leakage or official
   reproduction claims.
4. Qwen local bring-up only after a healthy local endpoint is available with
   `LOCAL_ONLY=true`.
