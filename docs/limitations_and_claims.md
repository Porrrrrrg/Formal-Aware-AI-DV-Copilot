# Limitations And Claims

## Current Claims

- JasperLoop-DV is a research prototype for JasperGold-in-the-loop AI DV assistance.
- Structured evidence packets provide a reproducible interface between formal evidence and LLM reasoning.
- Local deterministic scaffold runs validate evaluation plumbing and parser/schema behavior.
- JasperGold-backed claims are valid only for the checked RTL, harness, assumptions, properties, tool version, and command environment.
- RTL2Repair can intake arbitrary RTL files, draft candidate SVA, build debug bundles, and propose RTL patches for scratch recheck.

## Non-Claims

- The system is not production-ready.
- The agent cannot sign off RTL.
- The LLM is not the verification oracle.
- Deterministic scaffold results are not Codex results.
- A proof pass is not a proof of user intent equivalence.
- Parser support is conservative and fixture-driven, not a guarantee across every JasperGold version or TCL flow.
- The FVEval subset is not an official FVEval reproduction unless the exact external flow is imported and run.
- Coverage witness extraction is complete only when report parser, trace parser, schema, prompt, and evaluation all consume witness events end to end.
- RTL2Repair does not provide production RTL signoff, full semantic equivalence, or complete specification inference for arbitrary RTL.
- RTL2Repair auto-intents are coverage aids and starting points for engineer-authored specifications.
- RTL repair patches are proposals. By default they apply to scratch copies and require formal recheck plus engineer review before use.

## Known Risks

- Small benchmark scale can overstate robustness.
- Author labels are useful for evaluation plumbing but are not independently discovered truth.
- Overconstraints and vacuous proofs can make an assertion look successful while checking little real behavior.
- Raw logs and generated reports can leak local paths or tool details; keep them out of git by default.
- External LLM prompt export requires explicit audit and acknowledgement.
- A passing target property after an RTL patch can still miss regressions unless prior accepted SVAs and native benchmark properties are re-run.

## Pending Work

- Run real Codex benchmark subsets only after prompt audit, healthcheck, and small approved pilot runs.
- Expand parser fixtures with more JasperGold report variants.
- Bind JasperGold result summaries to run id, git SHA, tool version, and command manifest.
- Improve coverage witness trace extraction beyond the current parser interface and fixtures.
