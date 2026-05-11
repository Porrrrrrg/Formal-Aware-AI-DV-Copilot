# Stage 4A SVA Repair Ablation Final Jasper Proof

Created UTC: `2026-05-11T14:32:54Z`

## Scope

This report records live Moore/JasperGold syntax/proof/vacuity checks for the sanitized Stage 4A SVA repair ablation handoff artifact from #37. It does not run Qwen, does not rerun Codex, and does not modify benchmark labels.

Raw Jasper logs, generated harnesses, traces, `jgproject` directories, and license output remain local-only under ignored `jasper/reports` paths and are not committed.

## Inputs

- Base git SHA: `58b1ec13b5ebc26272826b6dcf98c7326e746e8a`
- Source artifact: `reports/repair/artifacts/sva_repair_ablation_candidates_20260511T064252Z.jsonl`
- Source artifact SHA-256: `62EB2DF8DA4048A1B5F2F16DB2BBA3DA377A0BDCC064B737ACED5CC937B568EC`
- Moore host: `moore.wot.ece.northwestern.edu`
- JasperGold: `/vol/cadence2018/XCELIUM1809/tools.lnx86/jasper/bin/jg` (`2018.09p002 64 bits`)
- Candidate rows checked: `126`
- Variants checked: `7`
- Repair cases covered per variant: `18`

## Aggregate Result

| Metric | Count |
| --- | ---: |
| Candidate count | 126 |
| Case count | 18 |
| Syntax pass | 126/126 |
| Proven | 126/126 |
| Not flagged vacuous | 126/126 |
| Falsified | 0/126 |
| Vacuous | 0/126 |
| Unknown or timeout | 0/126 |

Vacuity caveat: `jasper_vacuity_status` was null for all 126 candidates. `not_flagged_vacuous` therefore means proven and not parsed as vacuous by this runner, not an independent explicit non-vacuity certificate.

## Variant Metrics

| Variant | Local scaffold | Local exact match | Handoff candidates | Syntax pass | Proven | Not flagged vacuous | Falsified | Vacuous | Unknown/timeout | pass@1 | pass@k |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `baseline_prompt` | 13/18 | 13/18 | 18 | 18/18 | 18/18 | 18/18 | 0/18 | 0/18 | 0/18 | 18/18 | 18/18 |
| `cex_aware_prompt` | 13/18 | 13/18 | 18 | 18/18 | 18/18 | 18/18 | 0/18 | 0/18 | 0/18 | 18/18 | 18/18 |
| `signal_whitelist_only` | 13/18 | 13/18 | 18 | 18/18 | 18/18 | 18/18 | 0/18 | 0/18 | 0/18 | 18/18 | 18/18 |
| `temporal_hint_only` | 12/18 | 12/18 | 18 | 18/18 | 18/18 | 18/18 | 0/18 | 0/18 | 0/18 | 18/18 | 18/18 |
| `one_round_repair` | 12/18 | 12/18 | 18 | 18/18 | 18/18 | 18/18 | 0/18 | 0/18 | 0/18 | 18/18 | 18/18 |
| `multi_round_repair` | 13/18 | 13/18 | 18 | 18/18 | 18/18 | 18/18 | 0/18 | 0/18 | 0/18 | 18/18 | 18/18 |
| `self_check_before_final` | 12/18 | 12/18 | 18 | 18/18 | 18/18 | 18/18 | 0/18 | 0/18 | 0/18 | 18/18 | 18/18 |

For this handoff artifact, each variant has one committed candidate per case. The Stage 4A local manifest reports 29 internal candidates for `multi_round_repair`, but the sanitized Moore handoff contains only the selected/final row per case. As a result, pass@k in this report is computed over the committed handoff candidates and equals pass@1 for every variant. It is not evidence about uncommitted internal multi-round candidates.

## Interpretation Boundary

- Local scaffold success, exact-template match, selected-output Jasper proof, and best-of-candidates proof are separate layers.
- All 126 handoff candidates were syntax-clean and proven on Moore, including candidates that did not match the local reference template. This means final Jasper proof alone does not establish intent alignment for these repair cases.
- Best-of-candidates pass@k is an upper-bound search metric over available candidates. It is not single-output repair success.
- This PR does not claim production readiness, full signoff automation, or Qwen/Codex comparison.

## Commands

- `git archive local origin/main-equivalent branch and unpack on Moore due transient GitHub fetch 500 from Moore`
- `python3.11 temporary adapter: reports/repair/artifacts/sva_repair_ablation_candidates_20260511T064252Z.jsonl -> artifacts/sva_repair_ablation_for_final_proof.jsonl`
- `bash scripts/run_moore_codex_repair_final_proof.sh --dry-run --artifact artifacts/sva_repair_ablation_for_final_proof.jsonl --no-hash-check --out-root jasper/reports/sva_repair_ablation_final_proof --manifest-out reports/jasper/sva_repair_ablation_final_proof_dry_run_manifest.json`
- `tcsh -f -c 'source /vol/eecs391/cadence.env; setenv JASPER_BIN /vol/cadence2018/XCELIUM1809/tools.lnx86/jasper/bin/jg; bash scripts/run_moore_codex_repair_final_proof.sh --artifact artifacts/sva_repair_ablation_for_final_proof.jsonl --no-hash-check --out-root jasper/reports/sva_repair_ablation_final_proof --manifest-out reports/jasper/sva_repair_ablation_raw_final_proof_manifest_moore.json'`
- `python3.11 -m json.tool reports/jasper/sva_repair_ablation_raw_final_proof_manifest_moore.json`
