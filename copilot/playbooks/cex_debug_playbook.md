# Counterexample Debug Playbook

Purpose: turn a counterexample into a grounded DV diagnosis and a next action. The process is independent of model backend and formal tool vendor.

## Inputs

- Property intent and assertion or assumption text.
- Failure cycle, waveform summary, and relevant signal values.
- Active assumptions, reset/clock information, and coverage reachability evidence.
- RTL context and signal role map when available.
- Tool status: fail, bounded fail, inconclusive, vacuous, or unavailable.

## Debug Flow

1. Anchor the failure.
   - Record the failing property, failing cycle, and first cycle where the trigger became true.
   - Separate antecedent satisfaction, consequent failure, and reset/disable behavior.
   - Identify whether the trace starts from reset, post-reset, or unconstrained initial state.

2. Trace causality backward.
   - Follow control handshakes, valid/ready pairs, counters, FSM state, and data captures from failure to trigger.
   - Mark any impossible input behavior allowed by missing assumptions.
   - Mark any expected design response that did not occur despite legal inputs.

3. Classify the issue.
   - `rtl_design_bug`: legal stimulus violates a real requirement.
   - `assertion_property_bug`: property is stronger, weaker, or temporally different from intent.
   - `assumption_constraint_bug`: environment hides legal behavior or permits impossible behavior.
   - `testbench_stimulus_bug`: simulation or replay stimulus does not match intended scenario.
   - `reachable_coverage_gap`: unhit coverage goal has a witness or plausible legal path.
   - `unreachable_or_invalid_coverage_goal`: goal conflicts with spec, RTL architecture, or assumptions.

4. Choose a next action.
   - Fix RTL only when the trace is legal and the property matches intent.
   - Fix the assertion when timing, guard, reset, or signal scope is wrong.
   - Fix assumptions when the trace is impossible or the trigger is blocked.
   - Add directed stimulus when coverage is reachable but unhit.
   - Prove unreachable or waive only with owner-reviewed rationale.

## CEX Review Checklist

- The trace values cited are present in the supplied evidence.
- The failing cycle and trigger cycle are not conflated.
- Reset behavior is accounted for.
- Known protocol constraints are checked before calling a trace real.
- The diagnosis lists at least one falsifiable piece of evidence.
- The recommendation can be rerun or reviewed with a concrete artifact.

## Claim Boundaries

- A single CEX can refute a property but does not prove the full diagnosis alone.
- A proof pass after repair does not imply the assertion still matches intent.
- `not_flagged_vacuous` is not an explicit non-vacuity certificate.
- JasperLoop-DV recommendations are engineering aids, not production signoff automation.
