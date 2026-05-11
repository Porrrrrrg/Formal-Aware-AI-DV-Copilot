# Stage 3 Research Delta

Created UTC: 20260511T060137Z

Base commit: `5201ea212fb044d18b34b3154ad19474e7e8e4b2`

## What Changed

Stage 3 moved the project from a Stage 2 Codex scaffold-repair metric toward a
tool-checked formal repair artifact, while also expanding benchmark breadth.

The most important evidence change is #32: restored Codex SVA repair candidates
were checked live on Moore with JasperGold. The report covers 34 sanitized repair
candidates across 18 repair cases. Candidate-level syntax passed for 34/34, proof
passed for 34/34, and no candidate was parsed as vacuous by the manifest.

The main benchmark change is #27: the local DV benchmark now includes a FIFO 1R1W
family and additional assumption/vacuity cases. The total local DV labeled case
count is 53, including 23 new labeled cases, 14 coverage-closure cases, 33 SVA
generation cases, and 23 SVA repair cases.

The external-anchor change is #26: the repository now contains a 30-case
FVEval-compatible subset with explicit source metadata, prompt-leakage safeguards,
and limitation wording. It is an import and local runner, not an official FVEval
reproduction.

## Evidence Now Supported

- The restored Stage 2D Codex repair candidates can be replayed into a Moore/JasperGold final-proof workflow.
- The committed #32 report supports live JasperGold syntax/proof outcomes for the 34 restored candidates.
- The FIFO/vacuity expansion supports broader local benchmark metadata and test coverage.
- The FVEval subset supports a small external benchmark import path with reference answers excluded from prompt payloads.

## Evidence Not Yet Supported

- #32 does not prove production-ready SVA repair automation.
- #32 does not turn best-of-candidates pass@k into single-output repair success.
- #32 does not provide an independent explicit non-vacuity certificate because parsed `jasper_vacuity_status` is null for all candidates.
- #27 does not provide live JasperGold evidence for the newly added FIFO and vacuity/assumption cases.
- #26 does not reproduce official FVEval results or commercial property-equivalence scoring.
- Qwen remains a readiness blocker only; no Qwen quality, cost, or Qwen-vs-Codex comparison is supported.

## Research Implications

The strongest current result is no longer just "11/18 scaffold repair success."
The stronger statement is that restored Codex repair candidates now have live
JasperGold syntax/proof outcomes on Moore, with candidate-level and case-level
metrics reported separately.

The key caveat is selection semantics. Pass@k is useful as an upper-bound search
signal, but the single-output system metric should use the selected or first
candidate only. Future reports should keep these two numbers separate.

The benchmark expansion improves research credibility by adding FIFO behavior,
reset, ordering, overflow/underflow, simultaneous push/pop, liveness, and
assumption/vacuity examples. These cases should be validated with Moore evidence
before they become formal-result claims.

The FVEval subset improves external comparability, but only as a local
compatibility anchor. It should not be described as an apples-to-apples benchmark
until the metric stack matches the official flow.

## Recommended Next Experiments

1. Analyze the Stage 2D and #32 SVA repair cases at case level, separating selected-output pass@1 from best-of-candidates pass@k.
2. Add explicit vacuity extraction or a separate vacuity command path on Moore so "non-vacuous" can become a stronger certificate.
3. Run Moore evidence generation for the new FIFO and vacuity/assumption cases from #27.
4. Use the expanded repair set to rerun a small Codex repair subset only after the case-level analysis is complete.
5. Bring Qwen back only as a local readiness/subset task once a healthy local endpoint is available and `LOCAL_ONLY=true` is verified.
