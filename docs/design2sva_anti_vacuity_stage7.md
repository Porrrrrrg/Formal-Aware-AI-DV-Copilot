# Design2SVA Anti-Vacuity Stage 7

## Scope

Stage 7 turns the Stage 6 JasperGold subset result into an anti-vacuity repair
target. It does not claim broad Design2SVA success. The goal is narrower: detect
weak or vacuous generated assertions, make reachability visible before proof is
counted, and evaluate whether bounded repair improves formal usefulness.

## Why Stage 6 Was Useful

Stage 6 was a negative result, but it was the right kind of negative result.
The Codex candidates were schema-valid, syntax-clean, and stayed within visible
signals, yet JasperGold reported `unreachable` for the checked rows. That showed
that JSON validity, local syntax, and non-hallucinated signal use are not enough
to treat a Design2SVA candidate as useful.

The run also validated the evaluation path:

- Real candidates can be replayed into typed Design2SVA result artifacts.
- JasperGold status can override optimistic scaffold metrics.
- `unreachable` and `uncovered` outcomes are formal failures, never passes;
  Stage 7 separates unreachable antecedents and unreachable cover goals from
  generic weak/vacuous assertions.
- Repair needs first-class formal feedback, not only reference-like syntax.

## Reachability-Aware Repair Loop

Stage 7 should check reachability before treating an assertion proof as useful.
For each candidate, the loop is:

1. Derive a companion cover goal from the assertion trigger or antecedent.
2. Run the cover goal under the same clock, reset, harness, and assumptions.
3. If the cover is unreachable or uncovered, repair the antecedent, reset
   handling, or selected RTL context before rechecking the assertion.
4. If the cover is reachable, run the assertion proof and vacuity check.
5. Feed distinct statuses such as `unreachable_antecedent`,
   `unreachable_cover_goal`, `weak_vacuous_assertion`, `overstrong_assertion`,
   and `proven_non_vacuous` into the next repair step.

A repaired candidate should count as useful only when the relevant behavior is
reachable and the assertion has a measured non-vacuous formal result. A syntax
pass alone remains an infrastructure metric.

## Dry-Run And Replay Boundaries

Dry-run mode is local scaffolding. It can validate task loading, schema shape,
candidate plumbing, and metric aggregation, but it does not measure hosted model
quality or formal correctness.

Replay mode reuses existing candidate artifacts instead of sending new prompts.
It is useful for deterministic debugging and for rerunning JasperGold checks
against fixed inputs. Replay results should be reported as replay/formal
evidence, not as new LLM generation performance.

Only runs that explicitly record both candidate provenance and JasperGold
results should contribute to `proven@*`, `non_vacuous@k`, or anti-vacuity repair
claims.

## Claim Boundary

Supported:

- JasperLoop-DV detects weak or vacuous Design2SVA candidates.
- JasperLoop-DV can evaluate anti-vacuity repair with reachability-aware
  JasperGold feedback.
- Stage 7 can measure whether cover-before-assert repair improves formal
  usefulness on the checked subset.

Not yet supported:

- Broad Design2SVA success.
- Production signoff.
- ProofLoop-level performance.
- Any claim that syntax-clean or JSON-valid candidates are functionally correct
  without measured reachability, proof, and vacuity evidence.
