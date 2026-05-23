# Stage 2 Risk Register

UTC timestamp: 20260511T022509Z

This register reflects the Stage 2 evidence synthesis as of this timestamp. It does not introduce new benchmark results.

| ID | Priority | Risk | Evidence | Impact | Mitigation |
| --- | --- | --- | --- | --- | --- |
| R1 | P0 | SVA repair residual behavioral failures | Stage 2D Codex SVA repair succeeded on 11/18 scaffold cases, with 7 residual misses. | Repair quality is the largest observed real-model limitation; syntax-valid output is not enough. | Perform failure-case analysis, separate syntax from semantic/temporal repair, and add final JasperGold proof checks for model outputs. |
| R2 | P0 | No local Qwen quality evidence | Stage 2E found no local endpoint on vLLM, SGLang, or Ollama; subset status was not run. | Any Qwen readiness or quality statement would be unsupported. | Bring up a local Qwen server, rerun readiness with `LOCAL_ONLY=true`, then run only a small local subset before considering full Qwen. |
| R3 | P0 | Invalid model-route comparisons | Codex full pass exists; Qwen subset/full pass does not. Scaffold and Jasper summaries are deterministic/fallback evidence. | Headline Qwen versus Codex or local versus cloud claims would mix incomparable evidence classes. | Keep reports stratified by evidence class and require matched manifests before comparison. |
| R4 | P1 | SVA repair proof gap for Codex outputs | Stage 2D records `proven_final` as 0/18 because no live final JasperGold proof was run. | Scaffold success can overstate formal correctness. | Run formal proof validation on model-produced repaired assertions after repair-loop behavior is improved. |
| R5 | P1 | Coverage result may be underpowered | Stage 2D coverage was 9/9, with only 9 total coverage cases. | 100% accuracy may not generalize to broader coverage goals or designs. | Expand coverage cases, include more unreachable and invalid goals, and retain wrong-test-suggestion metrics. |
| R6 | P1 | Triage residual confusion between stimulus bugs and reachable gaps | Stage 2D had 2/30 errors: `arbiter_A8` and `rv_B8` predicted reachable coverage gaps instead of testbench stimulus bugs. | Downstream actions could add directed tests when stimulus/testbench repair is needed. | Add focused triage examples and ablations around stimulus observability, expected stimulus, and coverage reachability distinctions. |
| R7 | P1 | Deterministic scaffold results can be misread as LLM quality | Scaffold baseline reports 100% structured results for multiple tasks. | Inflated claims if deterministic fallback is merged with real model results. | Keep scaffold rows labeled as deterministic plumbing evidence in all summaries and PR descriptions. |
| R8 | P2 | Jasper raw artifacts remain local-only | Moore summaries commit hashes and counts, but raw logs/traces/case packets are not committed. | Independent reviewers cannot inspect raw Jasper traces from repository alone. | Preserve local artifact hashes and provide controlled artifact access if required by review workflow. |
| R9 | P2 | Small design diversity | Current reports cover three designs: `apb_regblock`, `arbiter_rr2`, and `rv_buffer`. | Results may be design-family specific. | Expand benchmarks across additional protocols, deeper temporal properties, and larger RTL modules. |
| R10 | P2 | Prompt audit is limited | Prompt audit reports 9 prompts and approximate tokens, not route-specific token accounting for every full-pass output. | Cost/latency conclusions remain weak. | Add per-output token, latency, and route metadata in future model manifests. |

## Current Gating View

Proceed:

- Failure-case analysis for the 7/18 Codex SVA repair misses.
- Focused experiments that split syntax repair from semantic/temporal repair.
- Triage refinement for the 2/30 stimulus-bug confusions.
- Expanded coverage benchmark design while preserving the current 9-case result as a small-sample observation.

Freeze:

- Qwen quality claims.
- Qwen versus Codex comparisons.
- Production readiness or full signoff automation claims.
- Formal repair success claims for Codex until final JasperGold validation is run on model-produced repairs.
