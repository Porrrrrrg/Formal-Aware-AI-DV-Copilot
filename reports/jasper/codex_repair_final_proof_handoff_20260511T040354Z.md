# Codex Repair Final-Proof Moore Handoff

Created UTC: 2026-05-11T04:03:54Z

## Scope

This handoff prepares Moore-only JasperGold syntax/proof/vacuity validation for the restored Codex SVA repair outputs.

Input artifact:

- `reports/repair/artifacts/codex_repair_outputs_20260511T035613Z.jsonl`
- LF-normalized SHA256: `DB469CDAAAECF06953260CFFB1BD6EAA24A7B76E66F2CD56A4CAE44F8DBDBD9B`
- Rows: 34 repaired SVA candidates
- Cases: 18 repair cases

## Local Status

JasperGold was not run in this Windows environment. No syntax, proof, or vacuity success is claimed here.

All 18 repair cases are pending Moore execution.

## Moore Runner

Use:

```bash
tcsh -fc 'source /vol/eecs391/cadence.env; setenv JASPER_BIN /vol/cadence2018/XCELIUM1809/tools.lnx86/jasper/bin/jg; bash scripts/run_moore_codex_repair_final_proof.sh --manifest-out reports/jasper/codex_repair_final_proof_manifest_moore.json'
```

Dry-run harness/render check without JasperGold:

```bash
bash scripts/run_moore_codex_repair_final_proof.sh --dry-run --manifest-out artifacts/codex_repair_final_proof_dry_run_manifest.json
```

## Artifact Policy

The runner writes generated harnesses, Jasper project directories, raw logs, reports, and traces under `jasper/reports/codex_repair_final_proof/`, which is ignored by Git. Commit only lightweight summaries or manifests from `reports/jasper/`; do not commit raw Jasper logs, traces, license output, or `jgproject` directories.

## Expected Moore Output

The Moore run should produce a lightweight manifest with one row per restored candidate and aggregate counts for:

- candidate count and case count
- Jasper syntax pass/fail counts
- proven count
- vacuous count
- raw artifact policy and ignored `jasper/reports/` location
