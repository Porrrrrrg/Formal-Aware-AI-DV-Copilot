# Design2SVA Stage 11 Harness Root-Cause Ladder

Stage 11 is a reviewer-facing diagnostic layer for the Design2SVA harness
failures seen after the Stage 10 reference-oracle audit. Its purpose is to
separate benchmark validity, wrapper/embedding behavior, reset reachability, and
candidate antecedent reachability before making any claim about generation
quality.

## Diagnostic Ladder

Run or review the checks in this order. Later checks are only meaningful when
the earlier baseline is healthy.

### A. Native Benchmark Reference Proves?

Check the benchmark's own reference assertion in the benchmark's native formal
harness, before the Design2SVA wrapper or embedding path is involved.

Local dry-run mapping command:

```bash
python evaluation/run_design2sva_native_oracle.py \
  --dry-run \
  --out evaluation/results/design2sva_native_reference_oracle_jasper.json
```

- Proves: the RTL, native harness, assumptions, clock/reset contract, and
  reference property are at least capable of proving the intended task.
- Fails: stop and debug the benchmark, native harness, bound, assumptions, or
  task definition. A native failure means downstream Design2SVA failures cannot
  be attributed to candidate generation or wrapper embedding yet.

### B. Design2SVA Reference Embedding Proves?

Check the local `evaluation_metadata.reference_sva` through the Design2SVA
reference-oracle mode and wrapper.

When native oracle results are available, pass them into the Design2SVA runner:

```bash
python evaluation/run_design2sva_eval.py \
  --reference-oracle \
  --jasper-check \
  --native-oracle-results evaluation/results/design2sva_native_reference_oracle_jasper.json
```

- Native proves and embedding proves: the Design2SVA wrapper can preserve the
  benchmark reference well enough for the later reachability checks.
- Native proves but embedding fails: the strongest pointer is wrapper or
  embedding, not model generation. Inspect bind path, instance hierarchy, file
  order, clocking, reset polarity, `disable iff`, assumptions, and any SVA
  normalization performed while embedding the reference.
- Native fails and embedding fails: the embedding result is not diagnostic. Fix
  the native benchmark baseline first.

### C. Basic Reset/Post-Reset Cover Reachable?

Check a minimal cover that does not depend on a generated candidate, such as
reset released and at least one sampled post-reset cycle reached under the same
wrapper and assumptions.

- Covered: the wrapper can leave reset and observe normal sampled behavior.
- Uncovered: debug reset polarity, reset release assumptions, clock generation,
  top-level constraints, and proof bounds. Candidate antecedents may appear
  unreachable simply because no meaningful post-reset state is reachable.

### D. Candidate Antecedent Cover Reachable?

Check the companion `cover property` extracted from the candidate antecedent.
For an unconditional assertion, this is effectively the post-reset sampling
point under its clock and `disable iff`.

- Covered: the candidate trigger is reachable. If the assertion still fails,
  debug the assertion semantics, consequent, temporal operator, or task intent
  match.
- Uncovered while A, B, and C pass: the candidate is likely over-constrained or
  uses an impossible trigger. This is generation or repair feedback, not a
  wrapper root cause.
- Syntax or extraction failure: debug candidate syntax, unsupported helper code,
  or the antecedent extraction path before interpreting proof quality.

## Outcome Map

| A native reference | B Design2SVA reference | C reset/post-reset cover | D candidate antecedent cover | Meaning |
| --- | --- | --- | --- | --- |
| Fails | Any | Any | Any | Benchmark, native harness, assumptions, bound, or task definition is suspect. |
| Proves | Fails | Any | Any | Wrapper or embedding is suspect. Native-proves/embedding-fails is the key isolation signal. |
| Proves | Proves | Fails | Any | Reset, clock, assumption, or bound issue in the Design2SVA wrapper setup. |
| Proves | Proves | Covered | Fails | Candidate trigger is unreachable; use as generation or repair feedback. |
| Proves | Proves | Covered | Covered | Harness path is healthy enough to judge the candidate assertion result. |

## Claim Boundaries

- Stage 11 does not send external LLM prompts. It interprets native benchmark
  checks, local reference-oracle embedding checks, and reachability covers.
- Stage 11 does not claim successful Design2SVA generation. It only narrows
  whether failures are more likely in the benchmark baseline, wrapper/embedding,
  reset/post-reset reachability, or candidate antecedent.
- Dry-run and replay artifacts are diagnostic plumbing evidence only. They are
  not signoff, production proof, or a substitute for measured JasperGold runs.
- The Stage 10 reference oracle uses local fixture `reference_sva` values. Those
  references are not added to generation prompts and do not prove semantic
  equivalence for generated candidates.

## Stage 11 Subset Result

The initial Moore/JasperGold root-cause subset used three Design2SVA fixture
cases.

Native benchmark oracle:

- `native_reference_proves_count = 3`
- `native_proof_status_counts = proven=3`
- `candidate_embedding = false`

Design2SVA reference embedding with native oracle context:

- `reference_proven@1 = 0.000`
- `reference_non_vacuous@1 = 0.000`
- `reference_antecedent_reachable@1 = 0.333`
- `harness_reachability_status = unreachable`
- Failure split: `unreachable_antecedent=2`, `unreachable_cover_goal=1`
- Root-cause candidates: `design2sva_embedding_bug=3`

This isolates the next debugging target: the native benchmark references prove,
but the same fixture references fail when embedded through the Design2SVA
wrapper. The immediate work should inspect wrapper file order, generated harness
semantics, assumption binding, reset handling, and the generated property module
path before changing prompts or generating more candidates.
