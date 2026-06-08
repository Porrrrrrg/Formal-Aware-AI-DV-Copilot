# RTL2Repair Real LLM Patch Subset

This result is a placeholder for Issue #97. No real LLM RTL patch proposal run has been executed for this table yet.

| Case | Status | Stable target SVA | Patch source | Formal oracle | Accepted patch |
| --- | --- | --- | --- | --- | --- |
| `arbiter_rr2_bug_double_grant` | Pending | deterministic/manual | real LLM when explicitly configured | JasperGold | Pending |
| `rv_buffer_bug_overwrite` | Pending | deterministic/manual | real LLM when explicitly configured | JasperGold | Pending |
| `apb_regblock_bug_wrong_addr` | Pending | deterministic/manual | real LLM when explicitly configured | JasperGold | Pending |

## Metric Definitions

| Metric | Meaning |
| --- | --- |
| `valid_json_rate` | Fraction of RTL patch outputs matching `rtl_repair_candidate` schema. |
| `non_empty_diff_rate` | Fraction of outputs containing a non-empty unified diff. |
| `patch_safety_pass_rate` | Fraction passing path, scope, and RTL-only patch safety checks. |
| `scratch_apply_rate` | Fraction that apply cleanly to scratch RTL. |
| `target_closure_rate` | Fraction where target was falsified before patch and proven non-vacuous after patch. |
| `regression_pass_rate` | Fraction of regression candidates passing after patch recheck. |
| `accepted_patch_rate` | Fraction accepted by target closure plus regression gate. |
| `fallback_rate` | Fraction falling back to deterministic/no-patch behavior because the LLM route failed or was not used. |

## Boundary

Phase A evaluates whether a real LLM can propose RTL diffs when the target SVA and formal evidence are already grounded. It does not measure SVA generation quality, arbitrary RTL auto-repair, or production signoff.
