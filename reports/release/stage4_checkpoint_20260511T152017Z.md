# Stage 4 Release Checkpoint

Created UTC: `20260511T152017Z`

Checkpoint commit: `581102fbe91c2724b12faf7200da5db735f68d1f`

Planned tag: `stage4-checkpoint-581102f`

## Scope

This checkpoint freezes the Stage 4 evidence state after the Stage 3 release
baseline, Stage 4 gate reports, expanded benchmark Moore/JasperGold packet
evidence, FVEval-compatible subset evaluation, SVA repair ablation local
scaffold metrics, and SVA repair ablation Moore/JasperGold final-proof report
were merged to `main`.

This is a report-only checkpoint. It does not change code behavior, rerun
experiments, update schemas, modify benchmark labels, call Codex, call Qwen,
call JasperGold, call Moore, or claim production readiness.

## Baseline State

- Stage 3 checkpoint baseline remains recorded in
  `reports/release/stage3_checkpoint_20260511T062042Z.md` and
  `reports/release/stage3_result_ledger_20260511T062042Z.md`.
- Stage 4 gate/report baseline is recorded in
  `reports/status/stage4_gate_status_20260511T063622Z.md` and
  `reports/status/stage4_second_wave_gate_20260511T141346Z.md`.
- Expanded benchmark evidence now records 53/53 schema-valid prove-backed
  Moore/JasperGold evidence packets.
- The FVEval-compatible subset runner records a 30-case deterministic local
  evaluation with no answer leakage and no official reproduction claim.
- The SVA repair ablation records seven Codex-backed variants with local
  scaffold metrics, plus a later Moore/JasperGold proof report for the
  sanitized 126-candidate handoff artifact.
- Qwen remains not run for quality evaluation; the committed readiness report
  records local backend unavailability and no cloud fallback.

## Verification

Run on `stage/stage4-release-checkpoint` at
`581102fbe91c2724b12faf7200da5db735f68d1f` before report creation:

| Command | Result |
| --- | --- |
| `git rev-parse HEAD` | `581102fbe91c2724b12faf7200da5db735f68d1f` |
| `python -m pytest -q` | 270 passed |
| `python -m ruff check .` | All checks passed |
| `git diff --check` | Passed |

Final validation after report creation:

| Command | Result |
| --- | --- |
| `python -m pytest -q` | 270 passed |
| `python -m ruff check .` | All checks passed |
| `git diff --check` | Passed |
| `python -m json.tool reports/release/stage4_artifact_inventory_20260511T152017Z.json` | Passed |

## Claim Boundary

- `not_flagged_vacuous` is not an independent explicit non-vacuity certificate.
  It means the runner did not parse a candidate as vacuous under the committed
  manifest fields.
- Best-of-candidates pass@k is not single-output repair success. It is an
  upper-bound search metric over available candidates.
- Jasper proof does not imply intent alignment. Proven assertions can still be
  semantically misaligned with the intended repair or benchmark task.
- The FVEval-compatible subset evaluation is not an official FVEval
  reproduction and does not reproduce commercial property-equivalence scoring.
- Qwen-vs-Codex comparison is unsupported because Qwen has still not run on a
  comparable local quality subset.

## Release Decision

This checkpoint is suitable as the Stage 4 release baseline because it is
report-only, preserves the Stage 4 evidence boundaries, and points to committed
manifests for each supported claim. Stage 5 should start from the planned tag
`stage4-checkpoint-581102f` and should not mutate Stage 4 report claims.
