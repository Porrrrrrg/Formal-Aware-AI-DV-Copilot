# FVEval and ProofLoop Connection

## FVEval Connection

FVEval argues that SVA generation must be evaluated by formal tools. JasperLoop-DV adopts this by checking generated and repaired SVA with JasperGold and tracking syntax, proof, and vacuity status.

## ProofLoop Connection

ProofLoop argues for formal feedback in the loop. JasperLoop-DV adopts this loop for assertion repair and extends it to DV triage and coverage closure.

## Differentiation

JasperLoop-DV focuses on practical DV ownership decisions:

- Should the engineer fix RTL?
- Should the engineer fix the property?
- Is an assumption overconstraining the design?
- Is a coverage hole reachable, unreachable, or invalid?

This makes the project closer to a formal-aware DV assistant than a pure assertion generator.
