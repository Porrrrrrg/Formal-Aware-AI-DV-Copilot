# Coverage Closure Playbook

Purpose: classify unhit coverage goals and recommend a concrete closure action using formal reachability, coverage plans, assumptions, and available traces.

## Inputs

- Coverage goal name, requirement trace, and current hit count.
- Coverage plan and legal/illegal bin definitions.
- Regression or formal cover evidence, including witness traces when present.
- Assumptions, constraints, and known stimulus limitations.
- Owner-reviewed waiver policy.

## Closure Flow

1. Normalize the goal.
   - Identify the requirement or feature the goal represents.
   - Confirm whether the goal is legal, illegal, boundary, error, transition, or cross coverage.
   - Check whether the sampling event matches the intended observable behavior.

2. Classify the gap.
   - Reachable coverage gap: legal behavior with missing or insufficient stimulus.
   - Constraint-blocked gap: legal behavior excluded by assumptions or random constraints.
   - Invalid goal: bin conflicts with protocol, architecture, or sampling semantics.
   - Unreachable by design: architecture prevents the state or transition.
   - Needs rerun: evidence is stale, incomplete, or from mismatched manifest inputs.

3. Recommend the smallest closure action.
   - Add a directed sequence for reachable scenarios.
   - Adjust distributions or constraints for hard-to-hit legal combinations.
   - Fix assumptions or testbench constraints when legal behavior is blocked.
   - Prove unreachable and create an owner-reviewed waiver for invalid or unreachable goals.
   - Rerun with manifest parity when tool, seed, benchmark, or backend inputs differ.

4. Verify closure.
   - Re-run the relevant regression or cover proof.
   - Record the witness, hit count, or waiver artifact.
   - Confirm the change did not weaken unrelated coverage or assumptions.

## Prioritization

| Priority | Criteria | Action |
| --- | --- | --- |
| High | Requirement-critical, error path, protocol safety, or silicon escape risk | Directed test or formal proof first |
| Medium | Legal cross or boundary scenario with moderate risk | Bias constraints or add targeted sequence |
| Low | Redundant or low-risk scenario | Batch with other closure work |
| Waiver candidate | Proven unreachable or invalid with owner approval | Document waiver and evidence |

## Claim Boundaries

- Coverage closure does not guarantee absence of bugs outside the coverage model.
- Replay demo is not model performance.
- Qwen-vs-Codex claims require manifest parity before comparison.
- JasperLoop-DV is not production signoff automation.
