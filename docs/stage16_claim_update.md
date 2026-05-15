# Stage 16 Claim Update

Stage 16 moves Design2SVA from readiness to measured expanded benchmark evidence
on the validated 12-case local fixture set.

## Supported

- Expanded fixture formal validity: Stage 15 native references prove 12/12, and
  the repaired wrapper proves 12/12 references non-vacuously.
- Prompt safety: the expanded prompt audit covers 12 prompts and reports no
  `reference_sva`, no `expected_proof_status`, and no exact reference SVA text.
- Real Codex generation quality on this fixture set:
  - 36/36 outputs are real LLM outputs.
  - `valid_json_rate = 1.0`.
  - `fallback_rate = 0.0`.
  - `syntax@1 = 1.0` and `syntax@k = 1.0`.
  - `hallucinated_signal_rate = 0.0` after filtering SystemVerilog keywords from
    identifier checks.
- Formal measured Design2SVA result on the 12-case set:
  - `proven@1 = 0.75`.
  - `proven@k = 1.0` for k=3.
  - `non_vacuous@k = 1.0`.
  - `proven_non_vacuous@k = 1.0`.

## Partially Supported

- Codex can generate formally useful Design2SVA assertions on the local expanded
  benchmark when allowed k=3 candidates and evaluated with the repaired wrapper.
- The benefit of k=3 over k=1 is supported by the 0.75 to 1.0 improvement, but
  attribution to retrieval, prompt guidance, or repair requires ablation.

## Unsupported

- Production signoff or deployment readiness.
- Broad industrial generalization beyond this 12-case benchmark.
- ProofLoop-level performance.
- Claims that a single Codex sample is sufficient for all cases.
- Claims about larger FVEval-scale performance before running those benchmarks.

## Next Evidence Required

Stage 17 should run ablations over direct prompting, retrieval context,
reachability guidance, anti-vacuity repair, reference oracle, and native oracle
controls. The key question is no longer whether the expanded fixture set is
valid; it is which system component is responsible for the measured
`proven_non_vacuous@k = 1.0` result.
