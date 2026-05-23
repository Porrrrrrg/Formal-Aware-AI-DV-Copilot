# Final Result Index

This index lists the final Stage 18 result package and the Stage 16/17 source
artifacts it summarizes. It does not add new experiments.

## Headline Stage 16 Metrics

Measured on the local 12-case expanded Design2SVA benchmark with `k = 3`,
after native and wrapper reference-oracle validation:

| Metric | Value |
| --- | ---: |
| Cases | 12 |
| Real Codex candidates | 36 |
| `valid_json_rate` | 1.0 |
| `fallback_rate` | 0.0 |
| `syntax@k` | 1.0 |
| `proven@1` | 0.75 |
| `proven@k` | 1.0 |
| `non_vacuous@k` | 1.0 |
| `proven_non_vacuous@k` | 1.0 |

The formal metrics come from
`evaluation/results/design2sva_eval_codex_expanded_jasper.json`, which replays
the exact saved real Codex candidates through the repaired JasperGold wrapper.

## Required Source Links

- [Design2SVA results](../../evaluation/results/design2sva_results.md)
- [Design2SVA ablation results](../../evaluation/results/design2sva_ablation_results.md)
- [Stage 16 error analysis](../../docs/design2sva_stage16_error_analysis.md)
- [Research claims after Stage 16](../../docs/research_claims_after_stage16.md)
- [Stage 17 paper result package](../../docs/paper_result_package_stage17.md)
- [Stage 17 final demo script](../../docs/final_demo_script_stage17.md)

## Final Stage 18 Package

- [Final research report](jasperloop_dv_final_research_report.md)
- [Final claim boundary](../../docs/final_claim_boundary.md)
- [Final demo script](../../docs/final_demo_script.md)
- [Final presentation outline](../../docs/final_presentation_slides_outline.md)
- [Reproducibility checklist](../../docs/reproducibility_checklist.md)

## Claim Boundary

- JasperLoop-DV is a research prototype, not production signoff automation.
- The Stage 16 result is on a local 12-case Design2SVA benchmark, not arbitrary
  RTL.
- FVEval-compatible import exists, but this is not official FVEval reproduction
  unless separately run under that benchmark protocol.
