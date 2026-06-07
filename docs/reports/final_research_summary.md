# Final Research Summary

## Project Identity

JasperLoop-DV is a JasperGold-in-the-loop AI design verification copilot research prototype. Its central claim is not that an LLM can sign off RTL. The claim is that structured DV evidence, constrained JSON outputs, output-quality gates, and formal re-checks can make LLM-assisted DV workflows more auditable than raw prompting.

## Evidence Chain

```text
benchmark RTL/properties/cases
  -> structured evidence packet
  -> local LLM or deterministic agent output
  -> schema/fallback/hallucination validation
  -> task-level scoring
  -> JasperGold re-check where applicable
  -> curated final summaries
```

The strongest formal chain is for SVA repair: saved local Qwen final candidates were copied to a JasperGold-capable host and re-checked. The strongest triage chain is error-driven: assumption/vacuity and stimulus-vs-coverage weaknesses were fixed with structured evidence cues, validated in scoped real-model gates, then checked with full 53-case reruns.

## Final Best Metrics

See [final_results.md](../../evaluation/results/final_results.md) for the canonical result table.

Highlights:

- SVA repair: local Qwen, 23 cases, exact/repair success 0.913, hallucinated signal 0.043.
- SVA repair JasperGold re-check: 23 saved finals, 22/23 syntax pass, 22 proven, 0 falsified, 0 undetermined, 0 vacuous.
- Failure triage: local Qwen, 53 cases, valid JSON 1.000, fallback 0.000, hallucinated signal 0.000, issue/action 1.000/1.000.
- Coverage closure: local Qwen, 14 cases, gap/action 1.000/1.000.

## Key Case Studies

### `repair_fifo_reset_wrong_polarity`

The local Qwen SVA repair run reported a hallucinated signal, `out_valid`. JasperGold re-check then failed syntax for the saved candidate. This shows why hallucinated-signal measurement is a useful pre-formal warning.

### `repair_arbiter_single_req1_wrong_grant`

This candidate did not match the exact local template but proved under JasperGold. Proof pass and exact-template intent alignment are separate signals; this case still needs human intent review.

### Assumption/Vacuity Triage

The v1.1.2 full local Qwen run classified only 3/12 `assumption_constraint_bug` cases correctly. Structured assumption/vacuity cues improved the scoped real-model gate to 12/12 and transferred to the full v1.1.6 rerun.

### Stimulus-vs-Coverage Triage

`rv_B8` and `fifo_D17` showed that missing stimulus can be confused with reachable coverage closure. Derived `stimulus_context` cues fixed both cases in a scoped gate and transferred to the v1.1.8 full triage rerun.

## Supported Claims

- JasperLoop-DV provides a working repository-root implementation of a JasperGold-in-the-loop AI DV copilot prototype.
- The generic `JASPERLOOP_LLM_CMD` route supports real local LLM evaluation without relying on one CLI.
- Local Qwen/Qwen3-14B-AWQ can produce schema-valid outputs for the included SVA repair, failure-triage, and coverage-closure tasks.
- The evaluation stack reports JSON validity, fallback rate, LLM error rate, hallucinated-signal rate, task metrics, and formal status separately.
- JasperGold re-check confirmed 22/23 saved local Qwen SVA repair final candidates compile and prove under the project harnesses used for that run.
- Structured evidence improvements resolved the observed failure-triage weak classes in the current 53-case local benchmark.

## Non-Claims

- Not Codex CLI performance.
- Not official FVEval performance.
- Not production DV signoff.
- Not full semantic intent equivalence.
- Not JasperGold-backed validation for failure triage or coverage recommendations.
- Not evidence that larger models are required or better.
- Not a guarantee across arbitrary RTL, JasperGold versions, or unseen benchmark families.

## Limitations

- The benchmark is modest in scale and author-labeled.
- The final local LLM results are from local Qwen/Qwen3-14B-AWQ only.
- SVA repair and coverage closure were not rerun after triage-specific changes.
- JasperGold proof is scoped to harnesses, assumptions, and checked properties.
- Official FVEval reproduction remains future work.

## Next Work

- Expand benchmark cases, especially assumption/vacuity and stimulus-vs-coverage cases.
- Run ablations to separate evidence cues, prompt wording, and normalization.
- Improve SVA repair intent-equivalence metrics.
- Add official FVEval-style evaluation only if the exact data and formal metrics are available.
- Package reproducible local model/backend setup for external replication.
