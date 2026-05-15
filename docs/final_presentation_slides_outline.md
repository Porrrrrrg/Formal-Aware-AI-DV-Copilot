# Final Presentation Slides Outline

## Slide 1. Title

JasperLoop-DV: Formal-aware AI assistance for Design2SVA, SVA repair, triage,
and coverage closure.

Key point: the LLM proposes; JasperGold is the formal oracle when checks are
run.

## Slide 2. Motivation

DV engineers need help navigating RTL, assertions, assumptions,
counterexamples, coverage goals, and formal logs. Fluent LLM output is useful
only when it is attached to evidence and review boundaries.

## Slide 3. Failure Example

Syntax-clean SVA can still be weak, vacuous, unreachable, temporally wrong, or
checked through a broken wrapper. Stage 16 keeps syntax, proof, reachability,
vacuity, and wrapper parity as separate metrics.

## Slide 4. Architecture

Show the pipeline:

`RTL/spec/SVA/assumptions/coverage -> JasperGold or replay evidence -> typed backend result -> evidence packet -> agents -> candidate JSON -> JasperGold feedback/report`.

## Slide 5. Evidence Packet

Explain the evidence packet as the contract between formal artifacts and the
model. It includes visible signals, assumptions, property or coverage intent,
formal status where available, and allowed action labels. It excludes expected
labels and reference answers from prompts.

## Slide 6. JasperGold Oracle

JasperGold measures syntax, proof, counterexample, cover, and vacuity where
those checks are run. Dry-run and replay rows are useful for reproducibility,
but only JasperGold-measured rows support proof and non-vacuity claims.

## Slide 7. Wrapper Parity Debugging

Design2SVA initially had a native-proves/wrapper-fails confound. The repaired
wrapper had to prove the reference oracle before generated candidates could be
interpreted. Lesson: evaluate the harness before evaluating the model.

## Slide 8. Stage 16 Result

Headline table:

- 12 local Design2SVA cases.
- 36 real Codex candidates, `k = 3`.
- `valid_json_rate = 1.0`, `fallback_rate = 0.0`, `syntax@k = 1.0`.
- JasperGold replay: `proven@1 = 0.75`, `proven@k = 1.0`,
  `non_vacuous@k = 1.0`, `proven_non_vacuous@k = 1.0`.

## Slide 9. Ablation And Lessons

Stage 17 separates measured controls from placeholders:

- Native and wrapper oracle controls passed.
- Current Codex row is JasperGold-measured replay.
- Direct prompt, no retrieval, and no anti-vacuity rows are not run yet.
- pass@k matters: 9/12 cases solved at first candidate, 12/12 by k=3.

## Slide 10. Limitations

JasperLoop-DV is a research prototype, not production signoff automation.
Results are on a local 12-case Design2SVA benchmark, not arbitrary RTL. FVEval
importer and local subset infrastructure exist, but this is not official
FVEval reproduction.

## Slide 11. Future Work

Run matched component ablations, expand benchmarks and designs, improve
explicit vacuity/cover support, strengthen intent-alignment checks, and only
claim official FVEval reproduction after a separately documented official run.

## Slide 12. Demo

CLI-only flow:

1. Show result table.
2. Show prompt audit.
3. Run local replay/reference command.
4. Show JasperGold-measured artifact.
5. Show final claim boundary.
