# Limitations And Claims

## Supported Claims

- JasperLoop-DV is a research prototype for JasperGold-in-the-loop AI DV assistance.
- Structured evidence packets provide a reproducible interface between formal evidence and LLM reasoning.
- The generic `JASPERLOOP_LLM_CMD` route supports real local LLM evaluation without depending on one vendor CLI.
- Local Qwen/Qwen3-14B-AWQ reached 1.000/1.000 issue/action accuracy on the 53-case failure-triage benchmark after targeted structured-evidence improvements.
- Saved local Qwen SVA repair final candidates were re-checked with JasperGold: 22 of 23 passed syntax and proved under the project harnesses used for that run.
- RTL2Repair can intake arbitrary RTL files, draft candidate SVA, build debug bundles, propose RTL patches, apply them to scratch copies, and re-run target/regression SVA checks on patched manifests.

## Non-Claims

- The system is not production-ready.
- The agent cannot sign off RTL.
- The LLM is not the verification oracle.
- Deterministic scaffold results are not hosted LLM results.
- Local Qwen results are not Codex CLI results.
- A JasperGold proof pass is not full semantic intent equivalence.
- JasperGold-backed claims apply only to the checked RTL, harness, assumptions, properties, tool version, and command environment.
- Failure-triage and coverage recommendations are not JasperGold-backed unless a separate formal check is defined and run.
- The FVEval-compatible subset is not an official FVEval reproduction unless the exact external data and evaluation flow are imported and run.
- RTL2Repair does not provide production RTL signoff, full semantic equivalence, or complete specification inference for arbitrary RTL.
- RTL repair patches are proposals. By default they apply to scratch copies and require formal recheck plus engineer review before use.

## Known Risks

- The benchmark remains modest in scale.
- Author labels are useful for evaluation but are not independently discovered truth.
- Overconstraints and vacuous proofs can make an assertion look successful while checking little behavior.
- Parser support is conservative and fixture-driven, not a guarantee across every JasperGold version or Tcl flow.
- Raw logs and generated reports can leak local paths or tool details; keep them out of git by default.
- A passing target property after an RTL patch can still miss regressions unless prior accepted SVAs and native benchmark properties are re-run.

## Next Work

- Expand assumption/vacuity and stimulus-vs-coverage benchmark cases.
- Add ablations that separate derived evidence cues, prompt wording, and normalization.
- Improve SVA repair intent-equivalence metrics beyond exact-template match and proof pass.
- Reproduce official FVEval-style metrics only if the exact external flow is available.
- Expand RTL2Repair regression suites and patch-quality checks beyond the current target plus accepted-SVA gate.
