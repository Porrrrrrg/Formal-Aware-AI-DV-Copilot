# Design2SVA Stage 13 Fixed Wrapper Rerun

## Scope

Stage 13 replays committed Codex Design2SVA candidates through the repaired
Design2SVA wrapper from Stage 12. It does not generate new external LLM
prompts.

Inputs:

- Original Codex subset: `evaluation/results/design2sva_eval_codex_subset.json`
- Anti-vacuity-aware Codex subset:
  `evaluation/results/design2sva_eval_antivacuity_codex_new_subset.json`
- Native/reference context:
  `evaluation/results/design2sva_native_reference_oracle_jasper.json`

Outputs:

- `evaluation/results/design2sva_eval_codex_fixed_wrapper_rerun.json`
- `evaluation/results/design2sva_eval_antivacuity_codex_fixed_wrapper_rerun.json`
- `evaluation/results/design2sva_eval_reference_oracle_fixed_wrapper_sanity.json`

## Runner

The Stage 13 command is:

```bash
python evaluation/run_design2sva_fixed_wrapper_rerun.py
```

The runner extracts candidate JSON from the committed result artifacts and
passes those exact candidates into the existing Design2SVA evaluator. It sets
`llm_prompts_sent=false` in every Stage 13 payload and does not set `--llm`.

The generic evaluator also accepts committed result JSONs directly as replay
sources, for example:

```bash
python evaluation/run_design2sva_eval.py \
  --replay evaluation/results/design2sva_eval_codex_subset.json \
  --k 3 \
  --jasper-check
```

## Moore/JasperGold Result

The measured Stage 13 run was executed on Moore with Cadence/JasperGold and did
not send new external LLM prompts. It reuses the committed Codex candidate
artifacts from Stages 6 and 9.

| Artifact | cases | k | formal_metrics_status | syntax@k | proven@k | proven_non_vacuous@k | valid_json_rate | fallback_rate | hallucinated_signal_rate | root_cause_detail_counts |
| --- | ---: | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| `design2sva_eval_codex_fixed_wrapper_rerun.json` | 3 | 3 | `measured` | 1.000 | 1.000 | 1.000 | 1.000 | 0.000 | 0.000 | `assertion_proven_non_vacuous=9` |
| `design2sva_eval_antivacuity_codex_fixed_wrapper_rerun.json` | 3 | 5 | `measured` | 1.000 | 1.000 | 1.000 | 1.000 | 0.000 | 0.000 | `assertion_proven_non_vacuous=15` |
| `design2sva_eval_reference_oracle_fixed_wrapper_sanity.json` | 3 | 1 | `measured` | 1.000 | 1.000 | 1.000 | 1.000 | 0.000 | 0.000 | `reference_oracle_matches_native_formal_behavior=3` |

This changes the interpretation of the earlier Stage 6-9 negative results. With
the repaired wrapper and property-label handling, the previously committed Codex
candidates prove non-vacuously on the three-case subset. The earlier
`proven@k=0.0` result was dominated by wrapper/embedding issues, not by the
semantic quality of these candidates alone.

The Stage 13 runner can be rerun on Moore with:

```bash
python evaluation/run_design2sva_fixed_wrapper_rerun.py
```

On a local machine without JasperGold, the same command records
`formal_metrics_status=blocked`; that local blocked result is a tooling boundary,
not candidate-generation evidence.

## Claim Boundary

Supported:

- The repaired wrapper enables a fair rerun path for prior committed Codex
  Design2SVA candidates.
- The Stage 13 runner reuses committed candidates and result artifacts.
- No external LLM prompts are sent by the Stage 13 runner.
- The repaired wrapper enables the prior three-case Codex Design2SVA subsets to
  prove non-vacuously under JasperGold.

Unsupported:

- Broad Design2SVA success.
- Production signoff.
- Generalization beyond the measured three-case subset.
