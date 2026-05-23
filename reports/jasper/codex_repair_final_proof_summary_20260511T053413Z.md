# Codex Repair Final Jasper Proof Results

Created UTC: 20260511T053413Z

## Summary

This report records live Moore/JasperGold final-proof validation results for restored Codex SVA repair candidates. It validates 34 sanitized Codex repair candidates covering 18 SVA repair cases.

This is not a production-readiness claim, not full signoff automation, and not a Qwen/Codex comparison.

## Key Inputs

- Input JSONL: `reports/repair/artifacts/codex_repair_outputs_20260511T035613Z.jsonl`
- Input SHA256: `DB469CDAAAECF06953260CFFB1BD6EAA24A7B76E66F2CD56A4CAE44F8DBDBD9B`
- JasperGold binary: `/vol/cadence2018/XCELIUM1809/tools.lnx86/jasper/bin/jg`
- JasperGold version: `2018.09p002 64 bits`
- Moore host: `moore.wot.ece.northwestern.edu`
- Command manifest: `reports/jasper/codex_repair_final_proof_manifest_20260511T053413Z.json`

## Candidate-Level Results

- candidate_count: 34
- syntax_pass: 34 / 34
- proven: 34 / 34
- non_vacuous_proven: 34 / 34
- falsified: 0 / 34
- vacuous: 0 / 34
- timeout_or_unknown: 0 / 34

Note: `jasper_vacuity_status` is null for all candidates in the parsed manifest, and no candidate was parsed as `vacuous`. The `non_vacuous_proven` count therefore means proven and not flagged vacuous by this manifest, not an independent explicit non-vacuity certificate.

## Case-Level Results

- case_count: 18
- pass@1 selected/first candidate proven_not_flagged_vacuous: 18 / 18
- pass@k best-of-candidates proven_not_flagged_vacuous: 18 / 18

## Claim Boundary

Case-level best-of-candidates pass@k is not the same as single-output repair success. Best-of-candidates pass@k is reported only as an upper-bound search result. It is not reported as single-output repair success.

A case is not described as "Codex repaired successfully" unless the selected single output for that case is the evaluated candidate and it is proven without being flagged vacuous.

## Raw Artifact Policy

Raw Jasper logs, trace directories, generated harness dumps, `jgproject` directories, and license/tool output remain local-only under ignored `jasper/reports/codex_repair_final_proof/` paths. They are not committed.
