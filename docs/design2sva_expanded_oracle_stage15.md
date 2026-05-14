# Design2SVA Stage 15 Expanded Oracle Error Analysis

## Scope

Stage 15 interprets expanded-oracle diagnostics for Design2SVA before any
expanded real LLM run is launched. The purpose is to separate oracle and harness
validity from candidate-generation quality.

This stage does not send external LLM prompts. It should only analyze native
reference-oracle behavior, wrapper reference-oracle behavior, and per-design
failure patterns already produced by the evaluation harness.

## Diagnostic Matrix

### Native Pass + Wrapper Pass

The native benchmark flow proves the reference oracle, and the Design2SVA
wrapper proves the same reference behavior.

Diagnostic meaning:

- The design task has a valid reference property under the native formal flow.
- The wrapper can preserve the relevant clock, reset, DUT, harness assumptions,
  property binding, and assertion semantics for this case.
- If generated candidates fail after this result, the likely bottleneck moves to
  candidate generation, repair selection, or prompt/task interpretation.

This is the cleanest condition for using the case in later real LLM evaluation.

### Native Pass + Wrapper Fail

The native benchmark flow proves the reference oracle, but the Design2SVA
wrapper fails to prove the same reference behavior.

Diagnostic meaning:

- The reference property is not the immediate problem; it is valid in the native
  benchmark context.
- The Design2SVA wrapper, embedding path, schema normalization, clock/reset
  handling, property focus, or harness reconstruction is still suspect.
- Generated-candidate failures on this case should not be interpreted as LLM
  failures until wrapper parity is restored.

This condition is an oracle/harness validity failure for the wrapper path.

### Native Fail + Wrapper Fail

Both the native benchmark flow and the Design2SVA wrapper fail the reference
oracle.

Diagnostic meaning:

- The case does not currently provide a trustworthy positive oracle for
  evaluating generated SVA success.
- The bottleneck may be an invalid reference property, unreachable harness
  condition, wrong task definition, environment mismatch, or a design-specific
  formal setup issue.
- Wrapper debugging alone is insufficient, because the native/reference oracle
  is not establishing the expected behavior either.

This condition should be excluded from broad candidate-generation conclusions
until the native/reference oracle is repaired or intentionally reclassified.

### Mixed Per-Design Failures

Different designs fall into different native/wrapper outcome categories.

Diagnostic meaning:

- The aggregate pass rate may hide multiple root causes.
- Per-design labels should be kept separate instead of collapsing all failures
  into one Design2SVA generation metric.
- A design with native pass plus wrapper fail points to wrapper parity work,
  while a design with native fail plus wrapper fail points to oracle or native
  harness triage.
- Only designs with native pass plus wrapper pass provide clean evidence for a
  later generated-candidate evaluation.

Mixed failures should drive a filtered evaluation set, not a single global
success or failure claim.

## Next Decision Rule

Run expanded real LLM evaluation only if the native/reference oracle pass rate
is high.

If the native/reference oracle pass rate is low or mixed, first repair or
filter the oracle set. A real LLM run would otherwise mix candidate-generation
signal with oracle, wrapper, and harness validity failures.

## Claim Boundary

Supported:

- Stage 15 diagnoses oracle and harness validity for expanded Design2SVA
  evaluation.
- Native pass plus wrapper pass is the required clean condition before treating
  later candidate failures as candidate-generation evidence.
- Native/reference oracle pass rate is the gate for deciding whether an
  expanded real LLM run is meaningful.
- No external LLM prompts are sent by this stage.

Unsupported:

- Broad Design2SVA LLM success.
- Production signoff.
- Generalization beyond designs whose native/reference oracle and wrapper
  behavior have been checked.
- Any conclusion that a generated candidate failed because of LLM quality when
  the corresponding native/reference oracle or wrapper parity condition has not
  passed.
