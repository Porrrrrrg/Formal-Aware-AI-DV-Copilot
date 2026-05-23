# FVEval and ProofLoop Connection

## FVEval Connection

FVEval argues that syntax pass is not enough: generated SVA must be evaluated by formal tools and, where possible, functional/formal equivalence criteria. JasperLoop-DV adopts the formal-tool evaluation principle by checking generated and repaired SVA with JasperGold and tracking syntax, proof, and vacuity status when those checks are actually run.

The local `benchmarks/fveval_subset` runner is compatibility scaffolding and prompt-sanitization infrastructure. It is not an official FVEval reproduction and does not run FVEval's commercial functional-equivalence flow.

## ProofLoop Connection

ProofLoop argues for AST-indexed retrieval, structural design queries, and iterative solver feedback. JasperLoop-DV adopts the feedback-loop direction for assertion repair and now adds a lightweight RTL retrieval index plus typed JasperGold backend results. This is infrastructure inspired by ProofLoop, not a claim of ProofLoop-level performance.

## Differentiation

JasperLoop-DV focuses on practical DV ownership decisions:

- Should the engineer fix RTL?
- Should the engineer fix the property?
- Is an assumption overconstraining the design?
- Is a coverage hole reachable, unreachable, or invalid?

This makes the project closer to a formal-aware DV assistant than a pure assertion generator.

The project contribution is DV workflow packaging around evidence: repair,
triage, assumptions, vacuity, coverage closure, retrieval context, result
provenance, and handoff manifests. Any stronger Design2SVA or repo-scale claim
requires additional formal evaluation evidence.
