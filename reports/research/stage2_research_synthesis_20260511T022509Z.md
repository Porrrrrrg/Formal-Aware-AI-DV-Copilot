# Stage 2 Research Synthesis

UTC timestamp: 20260511T022509Z

## Scope

This synthesis summarizes Stage 2 evidence now present in the repository. It is a bounded research synthesis, not a production-readiness claim, not a Qwen versus Codex comparison, and not a final paper-level conclusion.

Primary sources inspected:

- `reports/research/eval_summary_20260510T214913Z.md`
- `reports/research/ablation_20260510T214913Z.md`
- `reports/jasper/moore_evidence_summary_20260511T004654Z.md`
- `reports/jasper/sva_generation_jasper_summary_20260511T004654Z.md`
- `reports/jasper/sva_repair_jasper_summary_20260511T004654Z.md`
- `reports/llm/codex_subset_summary_20260511T005800Z.md`
- `reports/llm/codex_schema_fix_summary_20260511_012033.md`
- `reports/llm/codex_full_summary_20260511T015713Z.md`
- `reports/llm/codex_full_error_cases_20260511T015713Z.md`
- `reports/local_llm/qwen_readiness_20260511T013853Z.md`

## Evidence Classes

### 1. Deterministic scaffold results

The initial research baseline is local deterministic/scaffold evidence only. It validates benchmark plumbing, manifest capture, structured-packet paths, and negative-control behavior. It does not measure a hosted LLM or local Qwen model.

Observed scaffold results:

| Task | Cases | Result | Interpretation |
| --- | ---: | --- | --- |
| Triage structured route | 30 | 30/30 issue/action accuracy | Structured packet scaffold can recover expected labels. This is not LLM evidence. |
| Coverage structured route | 9 | 9/9 gap/action accuracy | Coverage context is load-bearing. Small case count limits generality. |
| SVA generation structured route | 27 | 27/27 exact match | Template/scaffold route is stable, not model quality. |
| SVA repair structured loop | 18 | 18/18 repair success | Deterministic repair fallback can select references. This is not a model repair result. |

Ablations support that coverage context and assumption context matter for triage. Removing coverage context dropped structured triage accuracy to 63.3%, and a minimal packet dropped it to 40.0%. The `no_repair_loop` SVA repair ablation failed 18/18, indicating that repair-loop structure is necessary in the scaffold setting, but loop-enabled variants were not distinguishable because deterministic fallback selected known references.

### 2. JasperGold-backed evidence validation

The Moore/JasperGold evidence reports add formal-tool backing for evidence packets and deterministic SVA checks. They do not report Codex, Qwen, cloud LLM, or hosted LLM performance.

Verified facts:

| Evidence item | Result |
| --- | ---: |
| Evidence packets generated | 30 |
| Packets with Jasper reports | 30 |
| Packets with trace references | 30 |
| Evidence packet schema validation | passed, 30/30 |
| SVA generation Jasper cases | 27 |
| SVA repair Jasper cases | 18 |

For deterministic SVA generation, both direct and structured outputs were Jasper checked across 27 cases. The direct route had low exact-match rate, 6/27, despite Jasper syntax/proof pass, showing that proof pass alone is insufficient as an intent metric. The structured route reached 27/27 exact match in the deterministic setting.

For deterministic SVA repair, 18 Jasper-feedback cases reached final syntax pass, final proof, and non-vacuity under the scaffold/fallback path. The report also records `source_counts: structured_fallback: 18` and `fallback_rate: 1.000`, so this is formal validation of the deterministic repair path, not real LLM repair quality.

### 3. Real Codex subset and full benchmark results

Stage 2B first exposed schema-admission failures in real Codex subset evaluation. In the 3+3+3 diagnostic subset, SVA repair returned valid JSON for 3/3 cases, but triage and coverage failed schema validation and fell back for all 6 cases. The aggregate valid JSON rate was 3/9, fallback rate 6/9, and LLM error rate 6/9.

Stage 2C repaired response schema strictness and reran the same 3+3+3 subset. The rerun produced valid JSON for 9/9 case-level outputs, fallback 0/9, and LLM errors 0/9. This supports that the Stage 2B failure mode was schema compatibility for triage/coverage, not necessarily model inability. The same subset still showed SVA repair residual behavior risk: SVA repair was schema-valid with no fallback, but only 2/3 scaffold repair success.

Stage 2D is the main real Codex-backed benchmark measurement available in this repository. It used the explicit full pass: 18 SVA repair cases, 30 triage cases, and 9 coverage cases. It did not run Qwen and did not run live final JasperGold proofs for the Codex SVA repair outputs.

| Stage 2D metric | Result |
| --- | ---: |
| Cases attempted | 57 |
| LLM adapter outputs | 71 |
| Valid JSON | 71/71 |
| Fallback outputs | 0/71 |
| LLM errors | 0/71 |
| Schema drift | 0 |
| Hallucinated signal rate where defined | 0/48 |

Task-level Codex results:

| Task | Cases | Main result | Residual issue |
| --- | ---: | --- | --- |
| SVA repair | 18 | 11/18 scaffold repair success | 7/18 residual behavioral failures; final Jasper proof was not run, so proven final is 0/18 by evaluator output. |
| Triage | 30 | 28/30 issue/action accuracy | 2/30 residual errors, both testbench stimulus bugs predicted as reachable coverage gaps with directed-test actions. |
| Coverage | 9 | 9/9 gap/action accuracy | Encouraging but limited by only 9 cases and 3 invalid/unreachable cases. |

The SVA repair failures span syntax, overbroad-property, temporal/semantic, and reset-related cases. The observed failure set supports follow-up work separating syntax repair from semantic/temporal repair and adding counterexample-aware repair prompts. It does not support a claim that Codex repair is formally successful, because live final JasperGold proof was not run for those Codex outputs.

### 4. Local Qwen readiness status

Stage 2E found local Qwen readiness blocked. No local OpenAI-compatible endpoint was available on the probed vLLM, SGLang, or Ollama ports. `LOCAL_ONLY=true` was tested with dummy cloud variables, and the readiness report records that cloud fallback was not allowed and not called.

No Qwen subset was run. Therefore there is no local Qwen quality claim, no Qwen repair result, and no Qwen versus Codex comparison.

## What Is Supported By Evidence

- Structured evidence packets and schemas are stable enough to support deterministic scaffold evaluation across the Stage 2 tasks.
- Jasper-backed evidence packet generation is validated for 30 packets, with Jasper reports and trace references for all 30.
- Deterministic SVA generation and repair summaries can be formal-tool checked on Moore, but those are scaffold/fallback results.
- Codex structured-output schema compatibility improved from the Stage 2B subset blocker to Stage 2C subset success: valid JSON 9/9, fallback 0/9, LLM errors 0/9.
- The Stage 2D Codex full pass supports a real Codex structured-output stability claim for this benchmark instance: 71/71 valid JSON, fallback 0/71, LLM errors 0/71, schema drift 0.
- Codex triage and coverage show useful signal on the current benchmark: triage 28/30 issue/action accuracy and coverage 9/9 gap/action accuracy.

## What Is Not Supported

- Production readiness is not supported.
- Full signoff automation is not supported.
- A Qwen quality claim is not supported because Qwen was unavailable and no local subset ran.
- A Qwen versus Codex comparison is not supported.
- A final paper-level conclusion is not supported without expanded benchmark size, independent splits, final formal proof checks for model outputs, and model-route replication.
- SVA repair formal success for Codex is not supported because Stage 2D reports scaffold outcomes and `proven_final` is 0/18 by evaluator output due no live final JasperGold proof.
- Coverage generalization is not supported by 9/9 alone because the case count is small.

## Research Interpretation

Stage 2 now supports a narrower but useful conclusion: the evaluation stack can distinguish deterministic scaffolds, formal-tool-backed evidence validation, real Codex JSON behavior, and blocked local Qwen readiness. The strongest real-model evidence is Codex schema/output reliability across 71 outputs and high triage/coverage accuracy on this benchmark. The weakest real-model task is SVA repair, where 7/18 cases remain behaviorally unresolved under scaffold checks.

The dominant technical direction is not additional headline scoring. The next work should isolate why SVA repair fails, distinguish syntax repair from semantic/temporal repair, and test whether counterexample-aware prompts or repair-loop ablations improve behavior under real model outputs and final formal checks.
