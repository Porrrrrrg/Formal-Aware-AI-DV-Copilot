# Design2SVA Ablation Plan

This Stage 14 artifact is dry-run/replay-only. It sends no new external LLM prompts.

## Variants

| Variant | Runner mode | Cases | Metrics emitted | Objective |
| --- | --- | ---: | --- | --- |
| `direct_prompt` | `local_dry_run` | 12 | `syntax@1`, `syntax@k`, `proven@1`, `proven@k`, `non_vacuous@k`, `proven_non_vacuous@k`, `antecedent_reachable@k`, `valid_json_rate`, `fallback_rate`, `hallucinated_signal_rate`, `average_rounds`, `wrapper_parity_pass_rate` | Natural-language intent plus schema contract, without retrieval context. |
| `retrieval_context` | `local_dry_run` | 12 | `syntax@1`, `syntax@k`, `proven@1`, `proven@k`, `non_vacuous@k`, `proven_non_vacuous@k`, `antecedent_reachable@k`, `valid_json_rate`, `fallback_rate`, `hallucinated_signal_rate`, `average_rounds`, `wrapper_parity_pass_rate` | Add bounded RTL/harness retrieval context. |
| `retrieval_plus_reachability_guidance` | `local_dry_run` | 12 | `syntax@1`, `syntax@k`, `proven@1`, `proven@k`, `non_vacuous@k`, `proven_non_vacuous@k`, `antecedent_reachable@k`, `valid_json_rate`, `fallback_rate`, `hallucinated_signal_rate`, `average_rounds`, `wrapper_parity_pass_rate` | Add reachable-trigger guidance on top of retrieval context. |
| `retrieval_plus_anti_vacuity_repair` | `local_dry_run` | 12 | `syntax@1`, `syntax@k`, `proven@1`, `proven@k`, `non_vacuous@k`, `proven_non_vacuous@k`, `antecedent_reachable@k`, `valid_json_rate`, `fallback_rate`, `hallucinated_signal_rate`, `average_rounds`, `wrapper_parity_pass_rate` | Replay-safe placeholder for anti-vacuity repair rounds. |
| `reference_oracle` | `reference_oracle_local_dry_run` | 12 | `syntax@1`, `syntax@k`, `proven@1`, `proven@k`, `non_vacuous@k`, `proven_non_vacuous@k`, `antecedent_reachable@k`, `valid_json_rate`, `fallback_rate`, `hallucinated_signal_rate`, `average_rounds`, `wrapper_parity_pass_rate` | Evaluate fixture reference_sva through the Design2SVA wrapper path. |
| `native_oracle` | `native_oracle_mapping_dry_run` | 12 | `syntax@1`, `syntax@k`, `proven@1`, `proven@k`, `non_vacuous@k`, `proven_non_vacuous@k`, `antecedent_reachable@k`, `valid_json_rate`, `fallback_rate`, `hallucinated_signal_rate`, `average_rounds`, `wrapper_parity_pass_rate` | Validate fixture labels against the checked-in native benchmark flow. |

## Interpretation

- `direct_prompt`, `retrieval_context`, and reachability-guidance rows are local scaffold checks until real model outputs are supplied.
- `retrieval_plus_anti_vacuity_repair` exercises the repair-loop shape without sending prompts.
- `reference_oracle` and `native_oracle` are infrastructure controls, not model-performance rows.
- JasperGold-measured claims require rerunning the same variants with the formal backend available and preserving the resulting JSON artifacts separately.

## Claim Boundary

- Supported: ablation configuration, metric schema, and local replay/dry-run plumbing.
- Unsupported: production signoff, broad model quality, or semantic equivalence beyond measured local fixtures.
