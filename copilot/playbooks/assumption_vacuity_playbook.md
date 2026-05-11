# Assumption And Vacuity Playbook

Purpose: review whether assumptions and property triggers make a proof meaningful. This playbook treats vacuity as an evidence question, not a label to hide.

## Inputs

- Assumption manifest or assumption list with stated intent.
- Assertion properties, trigger conditions, and companion covers.
- Formal vacuity status, assumption checks, cover reachability, and proof status.
- Counterexample or witness traces when available.
- Owner notes about legal protocol behavior and unreachable states.

## Review Flow

1. Inventory constraints and triggers.
   - List each assumption with its intended environment rule.
   - List each property trigger or cover goal that should be reachable.
   - Mark assumptions that constrain reset, handshakes, outstanding counts, or error injection.

2. Check for overconstraint.
   - Look for assumptions that permanently block requests, grants, handshakes, resets releasing, or error paths.
   - Check contradictory terms such as a signal required both true and false in the same cycle.
   - Compare assumption intent with protocol legality, not with proof convenience.

3. Check for underconstraint.
   - Identify impossible protocol behavior allowed by missing stability, range, ordering, or mutual exclusion assumptions.
   - Treat false CEX traces as prompts to add justified assumptions, not as proof that the assertion is wrong.

4. Interpret vacuity conservatively.
   - A vacuous pass means the checked behavior may not have been exercised.
   - A tool result of `not_flagged_vacuous` means only that the configured check did not flag vacuity.
   - Require positive trigger reachability evidence for a non-vacuity claim.

5. Resolve findings.
   - If the trigger is unreachable due to assumptions, repair or relax assumptions.
   - If the trigger is architecturally unreachable, document an owner-reviewed waiver.
   - If the trigger is reachable but the property still fails, continue with CEX debug.
   - If the property proves and trigger cover is reachable, record both proof and reachability artifacts.

## Red Flags

- Assumption states an output behavior rather than an input environment rule.
- Reset is assumed stuck active or stuck inactive without a documented scenario.
- Legal simultaneous operations are globally forbidden.
- Error or backpressure paths are assumed away.
- A property was changed to add a rare or impossible guard after a failure.
- A report claims "non-vacuous" without trigger cover or tool certificate evidence.

## Claim Boundaries

- Proof pass does not imply intent alignment.
- `not_flagged_vacuous` is not an explicit non-vacuity certificate.
- Assumption review requires RTL/DV owner confirmation before soundness claims.
- JasperLoop-DV is not production signoff automation.
