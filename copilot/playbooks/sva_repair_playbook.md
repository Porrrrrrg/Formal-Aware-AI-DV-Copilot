# SVA Repair Playbook

Purpose: repair one SystemVerilog assertion while preserving the intended design rule and the available evidence boundary. This playbook is model-agnostic and applies to Codex, Qwen, replay, or any other backend that consumes the same structured context.

## Inputs

- Broken assertion text, property id, and intended behavior.
- Syntax, proof, counterexample, and vacuity status from the verifier when available.
- Clock, reset, and disable semantics.
- Allowed signal and helper identifier list.
- Relevant trace values around the failing or vacuous cycle.
- Active assumptions and known constraint risks.

## Repair Flow

1. Classify the failure before editing.
   - Syntax failure: make the smallest syntax-preserving edit.
   - Counterexample failure: compare expected behavior with observed trace behavior at the failing cycle.
   - Vacuity or assumption-risk finding: inspect the trigger and assumptions before strengthening the property.
   - Non-convergence: do not rewrite intent only to make the proof easier.

2. Preserve identity and scope.
   - Keep the property id unless the evidence says the id is wrong.
   - Use only signals and properties present in the supplied context.
   - Keep the original clock and reset unless the failure evidence points to a clock/reset mismatch.

3. Repair intent, not just proof status.
   - Add missing antecedent guards only when tied to the stated protocol, property intent, or trace evidence.
   - Correct off-by-one timing by reconciling `|->`, `|=>`, `##N`, `$past`, and `$stable` with the failure trace.
   - Avoid turning a meaningful consequent into a constant true condition.
   - Avoid narrowing the antecedent until the property no longer checks the intended scenario.

4. Recheck quality.
   - The antecedent is reachable under the current environment or has an explicit reachability question.
   - The consequent still covers the required effect.
   - Reset disable does not mask the failing behavior outside reset.
   - The repair does not introduce unknown signals or backend-specific syntax.

## Common Repair Patterns

| Symptom | Likely issue | Preferred action |
| --- | --- | --- |
| Parser or elaboration failure | Invalid SVA syntax or unsupported construct | Minimal syntax edit, then rerun syntax check |
| Failure one cycle early or late | Implication or delay mismatch | Adjust `|->`/`|=>` or delay token using trace timing |
| Failure during reset release | Incorrect disable condition | Align `disable iff` with documented reset polarity |
| Legal idle cycle fails | Missing protocol guard | Add the guard named by intent or trace evidence |
| Assertion proves but trigger never fires | Vacuity or overconstraint risk | Add/inspect cover on trigger and review assumptions |
| Consequent checks unrelated signal | Intent drift | Restore requirement signal set from intent/reference |

## Claim Boundaries

- A proof pass does not imply intent alignment.
- `not_flagged_vacuous` is not an explicit non-vacuity certificate.
- Replay output demonstrates plumbing and determinism, not model performance.
- Qwen-vs-Codex comparisons are unsupported without manifest parity.
- JasperLoop-DV is not production signoff automation.

## Output Expectations

- Repaired SVA candidate.
- Short explanation tied to evidence.
- Remaining risks, especially assumption risk, vacuity risk, or intent ambiguity.
- Recommended next verifier action: syntax check, proof rerun, vacuity check, or owner review.
