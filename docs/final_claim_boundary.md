# Final Claim Boundary

## Supported Claims

- JasperLoop-DV is a research prototype for evidence-indexed AI assistance in
  DV workflows.
- The LLM is not the verification oracle. JasperGold is the formal oracle for
  syntax, proof, counterexample, cover, and vacuity results when those checks
  are actually run.
- On the local 12-case expanded Design2SVA benchmark, after native and wrapper
  reference-oracle validation, Stage 16 real Codex candidates replayed through
  JasperGold reached `proven@1 = 0.75`, `proven@k = 1.0`,
  `non_vacuous@k = 1.0`, and `proven_non_vacuous@k = 1.0` for `k = 3`.
- The Stage 16 prompt audit supports the no-gold-in-prompt guarantee for the
  expanded Design2SVA prompts: no reference SVA, no expected proof status, no
  exact reference SVA text, and no Jasper evidence in prompt-visible content.
- Wrapper parity checks were necessary and useful. The project found and fixed
  a native-proves/wrapper-fails confound before citing the expanded candidate
  result.

## Partially Supported Claims

- Codex can generate formally useful Design2SVA assertions when used with the
  current JasperLoop-DV prompt structure, retrieval context, repaired wrapper,
  candidate sampling, and replay/repair path. This is supported only on the
  local 12-case benchmark.
- Sampling multiple candidates helps on this local benchmark: `proven@1 = 0.75`
  improves to `proven@k = 1.0` for `k = 3`. The same k-scaling behavior is not
  established for larger or different benchmark sets.
- The FVEval importer and local subset runner are useful compatibility
  infrastructure. They do not establish official FVEval reproduction or
  published-result comparability.
- Static intent-alignment checks are useful review aids, but they do not prove
  semantic equivalence between a generated property and the engineer's intent.

## Unsupported Claims

- JasperLoop-DV is a research prototype, not production signoff automation.
- Results are on a local 12-case Design2SVA benchmark, not arbitrary RTL.
- FVEval importer exists, but this is not official FVEval reproduction unless
  separately run.
- The project does not claim deployment readiness, unattended verification,
  industrial signoff, or replacement of DV engineer review.
- The project does not claim ProofLoop-level performance.
- The project does not claim that syntax-valid SVA is equivalent to formally
  useful SVA.
- The project does not claim that one Codex sample is sufficient for all
  Design2SVA cases.
- The project does not claim broad generalization across all clocks, resets,
  bind paths, assertion styles, RTL structures, or commercial tool
  configurations.
