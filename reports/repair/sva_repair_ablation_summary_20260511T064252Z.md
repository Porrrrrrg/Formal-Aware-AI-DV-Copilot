# Stage 4A SVA Repair Ablation Summary

Created UTC: 2026-05-11T06:42:53Z
Git SHA: `b9acdb4b768845780b777813714a89bc1b5b2353`

## Scope

This report records a controlled SVA repair ablation over the existing 18 repair cases. It does not run Qwen and does not modify benchmark labels.

Claim boundary: Scaffold success, selected-output Jasper proof, and best-of-candidates proof are separate metrics. Best-of-k is an upper-bound search metric, not single-output repair success. New Stage 4A outputs do not claim Jasper proof unless --jasper-check was run on Moore.

## Variant Results

| variant | prompt | max rounds | valid JSON | fallback | hallucinated | scaffold success | exact match | pass@1 | pass@k | Jasper proof |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | --- |
| baseline_prompt | baseline | 1 | 18 | 0 | 0 | 13/18 | 13/18 | not run | not run | not_run_moore_handoff_required |
| cex_aware_prompt | cex_aware | 1 | 18 | 0 | 0 | 13/18 | 13/18 | not run | not run | not_run_moore_handoff_required |
| signal_whitelist_only | signal_whitelist | 1 | 18 | 0 | 0 | 13/18 | 13/18 | not run | not run | not_run_moore_handoff_required |
| temporal_hint_only | temporal_hint | 1 | 18 | 0 | 0 | 12/18 | 12/18 | not run | not run | not_run_moore_handoff_required |
| one_round_repair | baseline | 1 | 18 | 0 | 0 | 12/18 | 12/18 | not run | not run | not_run_moore_handoff_required |
| multi_round_repair | baseline | 3 | 29 | 0 | 0 | 13/18 | 13/18 | not run | not run | not_run_moore_handoff_required |
| self_check_before_final | self_check | 1 | 18 | 0 | 0 | 12/18 | 12/18 | not run | not run | not_run_moore_handoff_required |

## Stage 3D Formal Reference

The Stage 3D Moore/JasperGold manifest remains the only live final-proof result for restored Codex repair candidates in this branch.

```json
{
  "candidate_level": {
    "candidate_count": 34,
    "syntax_pass": 34,
    "syntax_fail": 0,
    "proven": 34,
    "non_vacuous_proven_manifest_rule": 34,
    "falsified": 0,
    "vacuous": 0,
    "timeout_or_unknown": 0,
    "vacuity_status_note": "vacuity_status is null for all candidates; no candidate was parsed as vacuous. The non_vacuous_proven count means proven and not flagged vacuous by the manifest, not an independent explicit non-vacuity certificate."
  },
  "case_level": {
    "case_count": 18,
    "pass_at_1_first_candidate_proven_not_flagged_vacuous": 18,
    "pass_at_k_best_of_candidates_proven_not_flagged_vacuous": 18,
    "claim_boundary": "case-level best-of-candidates pass@k is not the same as single-output repair success."
  }
}
```

Stage 3D proof metrics apply to restored baseline Codex candidates, not to newly generated Stage 4A variant outputs unless separately checked.

## Moore Handoff Artifact

- Path: `reports\repair\artifacts\sva_repair_ablation_candidates_20260511T064252Z.jsonl`
- Rows: 126
- SHA256: `62EB2DF8DA4048A1B5F2F16DB2BBA3DA377A0BDCC064B737ACED5CC937B568EC`
- Sanitized: no raw prompt text, no raw Jasper logs.

## Notes

- Best-of-k is reported only as an upper-bound search metric, never as single-output repair success.
- Stage 4A generated candidates require Moore final proof before any new formal-success claim.
- `jasper_vacuity_status == null` in Stage 3D is not an independent explicit non-vacuity certificate.
