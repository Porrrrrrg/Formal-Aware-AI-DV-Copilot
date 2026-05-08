# Demo Script

## Demo 1: SVA Repair

1. Generate an intentionally weak or syntactically invalid assertion.
2. Run JasperGold.
3. Show the syntax/proof feedback.
4. Run the SVA repair agent.
5. Re-run JasperGold and show the repaired status.

## Demo 2: RTL Bug vs Assertion Bug

1. Use two fairness failures.
2. Case A: RTL turn update bug.
3. Case B: property missing request persistence.
4. Show that the triage agent recommends different owners and next actions.

## Demo 3: Assumption Bug / Vacuity

1. Prove a fairness property under an overconstraining assumption.
2. Run vacuity.
3. Show that the agent flags the assumption, not the RTL.

## Demo 4: Coverage Closure

1. Show an unhit but reachable alternating-grants cover.
2. Show an illegal double-grant cover that should be unreachable.
3. Compare directed-test recommendation versus waiver/proof recommendation.
