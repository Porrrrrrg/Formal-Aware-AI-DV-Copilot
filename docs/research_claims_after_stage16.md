# Research Claims After Stage 16

This note separates what the current JasperLoop-DV / Design2SVA evidence supports
from what remains only partially supported or unsupported. The boundary is the
checked-in local evidence after Stage 16, especially:

- `docs/stage16_claim_update.md`
- `docs/design2sva_expanded_codex_stage16_error_analysis.md`
- `evaluation/results/design2sva_results.md`
- `evaluation/results/design2sva_eval_codex_expanded_jasper.json`
- `evaluation/results/design2sva_reference_oracle_expanded_jasper.json`

## Supported

- Structured Design2SVA prompts can produce schema-valid candidates on the local
  Stage 16 benchmark. The expanded real Codex run reports `valid_json_rate =
  1.0`, `fallback_rate = 0.0`, and 36/36 real LLM outputs for 12 cases with
  `k = 3`.
- The repaired Design2SVA wrapper can fairly evaluate candidates for this local
  benchmark without the earlier known wrapper-parity confound. Stage 15 native
  references prove 12/12, and the repaired wrapper proves the same 12/12
  references non-vacuously before generated candidates are interpreted.
- On the 12-case local benchmark, Codex + JasperLoop-DV reaches
  `proven_non_vacuous@k = 1.0` with `k = 3` under JasperGold replay through the
  repaired wrapper.
- Syntax alone was insufficient in earlier stages. Earlier local Codex
  candidates could be schema-clean and syntax-clean while failing or remaining
  unmeasured at the formal proof and anti-vacuity levels.
- Wrapper parity checks were necessary. The project previously isolated a native
  reference-proves / wrapper-reference-fails condition, so generated-candidate
  quality could not be judged until wrapper parity was repaired and rechecked.

## Partially Supported

- Codex can generate formally useful Design2SVA assertions when used with the
  current JasperLoop-DV prompt structure, retrieval context, repaired wrapper,
  and replay/repair path. This is supported on the 12-case local benchmark, but
  attribution to any single component still needs ablation.
- Sampling multiple candidates helps on the local benchmark. Stage 16 improves
  from `proven@1 = 0.75` to `proven@k = 1.0`, but this does not prove the same
  k-scaling behavior outside these fixtures.
- The FVEval-compatible scaffolding and local subset import are useful for
  organizing benchmark-style evidence. They do not yet establish official
  FVEval reproduction or apples-to-apples comparison against published FVEval
  results.
- The repaired wrapper evidence supports local evaluation fairness against the
  checked-in oracle controls. It does not by itself prove the wrapper covers all
  relevant RTL structures, assertion styles, clocks, resets, binds, or tool
  configurations.

## Not Supported

- Production signoff or deployment readiness.
- Broad industrial generalization beyond the measured local fixture set.
- Official FVEval reproduction.
- Proof that this works on arbitrary RTL.
- Claims that one Codex sample is sufficient for all Design2SVA cases.
- Claims that the current result isolates whether prompting, retrieval,
  reachability guidance, wrapper parity, feedback repair, or candidate sampling
  is the dominant cause of the Stage 16 success.
