# JasperLoop-DV Result Tables

Created for Stage 6A from existing committed reports only. No experiments,
model calls, JasperGold/Moore runs, benchmark relabeling, or source-code changes
were performed for this consolidation.

## Table 1. Stage Summary

| Stage | Scope | Primary result | Claim boundary | Source report(s) |
| --- | --- | --- | --- | --- |
| Stage 2 | Initial Moore/JasperGold evidence packets, Codex subset/full runs, Qwen readiness, and response-schema hardening | 30 primary local-DV packets generated with Jasper reports and trace references; Codex full benchmark later recorded 57 attempted cases and 71/71 valid JSON | Early subset results and schema fixes are not production readiness; Qwen was initially blocked | `reports/jasper/moore_evidence_summary_20260511T004654Z.md`; `reports/llm/codex_full_summary_20260511T015713Z.md`; `reports/local_llm/qwen_readiness_20260511T013853Z.md`; `reports/llm/codex_schema_fix_summary_20260511_012033.md` |
| Stage 3 | Baseline release ledger, repair-output restore, final proof handoff, benchmark expansion, FVEval-compatible import | Stage 3 ledger froze Moore packets, Codex full benchmark, 34-candidate repair final proof, 53-case metadata expansion, and 30-case FVEval-compatible import | Benchmark expansion was metadata-only until later Moore evidence; best-of-k is not single-output success | `reports/release/stage3_result_ledger_20260511T062042Z.md`; `reports/repair/codex_repair_output_restore_summary_20260511T035613Z.md`; `reports/jasper/codex_repair_final_proof_summary_20260511T053413Z.md`; `reports/benchmarks/benchmark_expansion_summary_20260511T031851Z.md`; `reports/benchmarks/fveval_subset_import_20260511T031107Z.md` |
| Stage 4 | Expanded Jasper evidence, FVEval-compatible subset evaluation, SVA repair ablation, final proof for ablation candidates | 53/53 expanded local-DV cases have schema-valid prove-backed packets; 126/126 ablation handoff candidates syntax-pass and prove | Auxiliary cover/vacuity modes failed under the current Jasper command path; proof pass does not imply intent alignment | `reports/release/stage4_result_ledger_20260511T152017Z.md`; `reports/jasper/expanded_benchmark_evidence_summary_20260511T064639Z.md`; `reports/fveval/fveval_subset_eval_summary_20260511T141418Z.md`; `reports/repair/sva_repair_ablation_summary_20260511T064252Z.md`; `reports/jasper/sva_repair_ablation_final_proof_summary_20260511T143254Z.md` |
| Stage 5 | Unified CLI/workflow, Moore handoff automation, intent alignment, replay demo, local Qwen backend, repo hygiene | CLI/workflow surfaces exist; static intent alignment smoke produced 18 results; local Qwen 3+3+3 subset completed with valid JSON and no fallback | Workflow/demo evidence is integration evidence only; Qwen 3+3+3 is not a full Qwen benchmark | `reports/release/stage5_result_ledger_20260511T205601Z.md`; `reports/alignment/intent_alignment_smoke_summary_20260511T180423Z.md`; `reports/workflows/e2e_demo_summary_20260511T191259Z.md`; `reports/local_llm/qwen_workflow_subset_summary_20260511T202620Z.md` |
| Stage 5.5 | Skill import, playbooks/rules, prompt/workflow guidance, integration gate | 19 sanitized skills imported; five DV playbooks and four rule libraries added; prompt/workflow dry-runs reference playbook guidance | Skills and playbooks are guidance assets, not correctness evidence or new benchmark results | `reports/release/stage55_result_ledger_20260511T224417Z.md`; `reports/skills/skill_integration_gate_20260511T214452Z.md`; `reports/research/stage55_to_stage6_entry_plan_20260511T224417Z.md` |
| Stage 6A | Final report and consolidated result tables | Documentation packaging only | Does not rerun or reinterpret prior evidence beyond the boundaries recorded in source reports | `reports/research/stage55_to_stage6_entry_plan_20260511T224417Z.md` |

## Table 2. Benchmark And Case Counts

| Evidence set | Cases or rows | Breakdown | Status | Source report(s) |
| --- | ---: | --- | --- | --- |
| Primary local-DV evidence packets | 30 cases | `apb_regblock`: 10; `arbiter_rr2`: 10; `rv_buffer`: 10 | Schema validation passed; packets have Jasper report and trace references | `reports/jasper/moore_evidence_summary_20260511T004654Z.md` |
| Current expanded local-DV benchmark | 53 cases | `apb_regblock`: 12; `arbiter_rr2`: 12; `fifo_1r1w`: 17; `rv_buffer`: 12 | 53/53 schema-valid prove-backed packets in Stage 4B | `reports/jasper/expanded_benchmark_evidence_summary_20260511T064639Z.md` |
| Expanded issue-type distribution | 53 cases | RTL bug: 11; assertion bug: 12; assumption bug: 12; stimulus bug: 4; reachable coverage gap: 9; invalid/unreachable coverage goal: 5 | Author expected labels, not observed Jasper labels | `reports/benchmarks/benchmark_expansion_summary_20260511T031851Z.md` |
| SVA generation set after expansion | 33 cases | Includes 6 new FIFO generation cases | Metadata expansion; Stage 2 Moore evidence covered 27 generated candidates | `reports/benchmarks/benchmark_expansion_summary_20260511T031851Z.md`; `reports/jasper/moore_evidence_summary_20260511T004654Z.md` |
| SVA repair set after expansion | 23 cases | Includes 5 new FIFO repair cases | Metadata expansion; Codex and ablation proof reports cover the original 18-case repair set | `reports/benchmarks/benchmark_expansion_summary_20260511T031851Z.md`; `reports/jasper/codex_repair_final_proof_summary_20260511T053413Z.md`; `reports/jasper/sva_repair_ablation_final_proof_summary_20260511T143254Z.md` |
| Codex full benchmark | 57 cases | 18 SVA repair; 30 triage; 9 coverage | Real Codex-backed full pass; no Qwen comparison | `reports/llm/codex_full_summary_20260511T015713Z.md` |
| Codex repair final-proof candidates | 34 candidates / 18 cases | Restored Codex repair outputs | Live Moore/JasperGold proof validation | `reports/jasper/codex_repair_final_proof_summary_20260511T053413Z.md` |
| SVA repair ablation handoff | 126 rows | 7 variants x 18 repair cases | Local scaffold plus later Moore/JasperGold final proof | `reports/repair/sva_repair_ablation_summary_20260511T064252Z.md`; `reports/jasper/sva_repair_ablation_final_proof_summary_20260511T143254Z.md` |
| FVEval-compatible subset | 30 cases | 10 NL2SVA-Human; 10 NL2SVA-Machine; 10 Design2SVA | Local subset runner only; not official FVEval reproduction | `reports/benchmarks/fveval_subset_import_20260511T031107Z.md`; `reports/fveval/fveval_subset_eval_summary_20260511T141418Z.md` |
| Local Qwen workflow subset | 9 cases | 3 SVA repair; 3 triage; 3 coverage | Local-only workflow readiness subset | `reports/local_llm/qwen_workflow_subset_summary_20260511T202620Z.md`; `reports/local_llm/qwen_runtime_fix_summary_20260511T202643Z.md` |

## Table 3. Jasper Evidence

| Evidence report | Scope | Jasper/Moore outcome | Vacuity or cover boundary | Source report(s) |
| --- | --- | --- | --- | --- |
| Primary Moore evidence packets | 30 primary local-DV cases | 30 case packets generated; 30 with Jasper reports; 30 with trace references; schema validation passed | Raw logs and trace directories remained local-only | `reports/jasper/moore_evidence_summary_20260511T004654Z.md` |
| Stage 2 SVA generation and repair smoke evidence | SVA generation and repair candidates on Moore | 27 SVA generation Jasper cases and 18 SVA repair Jasper cases are recorded in the Moore summary | This report does not record Codex/Qwen/cloud performance | `reports/jasper/moore_evidence_summary_20260511T004654Z.md` |
| Expanded benchmark evidence | 53 current local-DV cases | 53 evidence packets generated; 53 report references; 53 trace-dir references; 53 schema-valid packets | Auxiliary cover runs 0/4 succeeded and auxiliary vacuity runs 0/4 succeeded due command support blockers | `reports/jasper/expanded_benchmark_evidence_summary_20260511T064639Z.md` |
| Codex repair final proof | 34 restored Codex repair candidates over 18 cases | 34/34 syntax pass; 34/34 proven; 0 falsified; 0 timeout/unknown | `non_vacuous_proven` means proven and not parsed as vacuous, not explicit non-vacuity certification | `reports/jasper/codex_repair_final_proof_summary_20260511T053413Z.md` |
| SVA repair ablation final proof | 126 handoff candidates over 18 cases and 7 variants | 126/126 syntax pass; 126/126 proven; 0 falsified; 0 unknown/timeout | `not_flagged_vacuous` is not an independent explicit non-vacuity certificate | `reports/jasper/sva_repair_ablation_final_proof_summary_20260511T143254Z.md` |

## Table 4. Codex Full Benchmark

| Task | Cases | LLM outputs | Valid JSON | Fallback | LLM error | Hallucinated signal | Main result | Source report(s) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |
| Aggregate | 57 | 71 | 71/71 = 100.0% | 0/71 = 0.0% | 0/71 = 0.0% | 0/48 = 0.0% for defined tasks | Schema drift count 0 | `reports/llm/codex_full_summary_20260511T015713Z.md` |
| SVA repair | 18 | 32 | 100.0% | 0.0% | 0.0% | 0.0% | 11/18 scaffold repair success; 11/18 final exact match; no live Jasper final proof in this evaluator | `reports/llm/codex_full_summary_20260511T015713Z.md`; `reports/llm/codex_full_error_cases_20260511T015713Z.md` |
| Triage | 30 | 30 | 100.0% | 0.0% | 0.0% | 0.0% | 28/30 issue and action accuracy | `reports/llm/codex_full_summary_20260511T015713Z.md` |
| Coverage | 9 | 9 | 100.0% | 0.0% | 0.0% | N/A | 9/9 gap and action accuracy; 6/6 reachable sequence presence | `reports/llm/codex_full_summary_20260511T015713Z.md` |

## Table 5. SVA Repair Final-Proof Table

| Metric | Value | Interpretation boundary | Source report(s) |
| --- | ---: | --- | --- |
| Candidate count | 34 | Sanitized restored Codex repair candidates | `reports/jasper/codex_repair_final_proof_summary_20260511T053413Z.md` |
| Case count | 18 | Original SVA repair cases represented by restored outputs | `reports/jasper/codex_repair_final_proof_summary_20260511T053413Z.md` |
| Syntax pass | 34/34 | Live Moore/JasperGold syntax/proof path | `reports/jasper/codex_repair_final_proof_summary_20260511T053413Z.md` |
| Proven | 34/34 | Proof pass under the checked harness and assumptions | `reports/jasper/codex_repair_final_proof_summary_20260511T053413Z.md` |
| Proven and not parsed vacuous | 34/34 | Not an independent explicit non-vacuity certificate because `jasper_vacuity_status` was null for all candidates | `reports/jasper/codex_repair_final_proof_summary_20260511T053413Z.md` |
| Falsified | 0/34 | No candidate parsed as falsified | `reports/jasper/codex_repair_final_proof_summary_20260511T053413Z.md` |
| Timeout or unknown | 0/34 | No candidate parsed as timeout/unknown | `reports/jasper/codex_repair_final_proof_summary_20260511T053413Z.md` |
| Case-level pass@1 | 18/18 | Selected/first candidate proven and not flagged vacuous | `reports/jasper/codex_repair_final_proof_summary_20260511T053413Z.md` |
| Case-level pass@k | 18/18 | Best-of-candidates upper-bound search result, not single-output success | `reports/jasper/codex_repair_final_proof_summary_20260511T053413Z.md` |

## Table 6. SVA Repair Ablation

| Variant | Prompt | Max rounds | Local valid JSON | Local fallback | Local hallucinated | Local scaffold success | Local exact match | Handoff candidates | Jasper syntax pass | Jasper proven | Jasper not flagged vacuous | pass@1 | pass@k | Source report(s) |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| `baseline_prompt` | baseline | 1 | 18 | 0 | 0 | 13/18 | 13/18 | 18 | 18/18 | 18/18 | 18/18 | 18/18 | 18/18 | `reports/repair/sva_repair_ablation_summary_20260511T064252Z.md`; `reports/jasper/sva_repair_ablation_final_proof_summary_20260511T143254Z.md` |
| `cex_aware_prompt` | cex_aware | 1 | 18 | 0 | 0 | 13/18 | 13/18 | 18 | 18/18 | 18/18 | 18/18 | 18/18 | 18/18 | `reports/repair/sva_repair_ablation_summary_20260511T064252Z.md`; `reports/jasper/sva_repair_ablation_final_proof_summary_20260511T143254Z.md` |
| `signal_whitelist_only` | signal_whitelist | 1 | 18 | 0 | 0 | 13/18 | 13/18 | 18 | 18/18 | 18/18 | 18/18 | 18/18 | 18/18 | `reports/repair/sva_repair_ablation_summary_20260511T064252Z.md`; `reports/jasper/sva_repair_ablation_final_proof_summary_20260511T143254Z.md` |
| `temporal_hint_only` | temporal_hint | 1 | 18 | 0 | 0 | 12/18 | 12/18 | 18 | 18/18 | 18/18 | 18/18 | 18/18 | 18/18 | `reports/repair/sva_repair_ablation_summary_20260511T064252Z.md`; `reports/jasper/sva_repair_ablation_final_proof_summary_20260511T143254Z.md` |
| `one_round_repair` | baseline | 1 | 18 | 0 | 0 | 12/18 | 12/18 | 18 | 18/18 | 18/18 | 18/18 | 18/18 | 18/18 | `reports/repair/sva_repair_ablation_summary_20260511T064252Z.md`; `reports/jasper/sva_repair_ablation_final_proof_summary_20260511T143254Z.md` |
| `multi_round_repair` | baseline | 3 | 29 | 0 | 0 | 13/18 | 13/18 | 18 | 18/18 | 18/18 | 18/18 | 18/18 | 18/18 | `reports/repair/sva_repair_ablation_summary_20260511T064252Z.md`; `reports/jasper/sva_repair_ablation_final_proof_summary_20260511T143254Z.md` |
| `self_check_before_final` | self_check | 1 | 18 | 0 | 0 | 12/18 | 12/18 | 18 | 18/18 | 18/18 | 18/18 | 18/18 | 18/18 | `reports/repair/sva_repair_ablation_summary_20260511T064252Z.md`; `reports/jasper/sva_repair_ablation_final_proof_summary_20260511T143254Z.md` |

For this handoff artifact, pass@k equals pass@1 because the committed Moore
handoff contains one selected/final row per case for each variant. This is not
evidence about uncommitted internal multi-round candidates.

## Table 7. Expanded Benchmark Evidence

| Metric | Value | Boundary | Source report(s) |
| --- | ---: | --- | --- |
| Total current benchmark cases attempted | 53 | Current local-DV benchmark after expansion | `reports/jasper/expanded_benchmark_evidence_summary_20260511T064639Z.md` |
| Stage 2 old Jasper-evidence baseline cases | 30 | Historical primary baseline | `reports/jasper/expanded_benchmark_evidence_summary_20260511T064639Z.md`; `reports/jasper/moore_evidence_summary_20260511T004654Z.md` |
| New FIFO cases | 17 | New `fifo_1r1w` family | `reports/jasper/expanded_benchmark_evidence_summary_20260511T064639Z.md`; `reports/benchmarks/benchmark_expansion_summary_20260511T031851Z.md` |
| New existing-design assumption/vacuity cases | 6 | Author-labeled expected metadata | `reports/jasper/expanded_benchmark_evidence_summary_20260511T064639Z.md`; `reports/benchmarks/benchmark_expansion_summary_20260511T031851Z.md` |
| Evidence packets generated | 53 | Packet-level prove-backed evidence | `reports/jasper/expanded_benchmark_evidence_summary_20260511T064639Z.md` |
| Schema-valid packets | 53 | Schema-invalid packets: 0 | `reports/jasper/expanded_benchmark_evidence_summary_20260511T064639Z.md` |
| Report references | 53 | `report_found` count | `reports/jasper/expanded_benchmark_evidence_summary_20260511T064639Z.md` |
| Trace-dir references | 53 | `trace_dir_found` count | `reports/jasper/expanded_benchmark_evidence_summary_20260511T064639Z.md` |
| Trace file references | 610 | References in packets; raw traces remain local-only | `reports/jasper/expanded_benchmark_evidence_summary_20260511T064639Z.md` |
| Prove runs | 15/15 succeeded | Successful prove reports back the evidence packets | `reports/jasper/expanded_benchmark_evidence_summary_20260511T064639Z.md` |
| Auxiliary cover runs | 0/4 succeeded | `cover -all` unsupported in the current Jasper 2018.09 command path | `reports/jasper/expanded_benchmark_evidence_summary_20260511T064639Z.md` |
| Auxiliary vacuity runs | 0/4 succeeded | `check_vacuity` unavailable in the current benchmark TCL command set | `reports/jasper/expanded_benchmark_evidence_summary_20260511T064639Z.md` |

## Table 8. FVEval-Compatible Subset

| Subset | Cases | Syntax scaffold | Valid JSON | Fallback | Hallucinated signals | Exact/reference match | Jasper | Source report(s) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |
| Aggregate | 30 | 30/30 | 30/30 | 30/30 | 0/30 | 0/20 reference-eligible cases | not run | `reports/fveval/fveval_subset_eval_summary_20260511T141418Z.md`; `evaluation/results/fveval_subset_results.md` |
| NL2SVA-Human | 10 | 10/10 | 10/10 | 10/10 | 0/10 | 0/10 | not_run | `reports/fveval/fveval_subset_eval_summary_20260511T141418Z.md`; `evaluation/results/fveval_subset_results.md` |
| NL2SVA-Machine | 10 | 10/10 | 10/10 | 10/10 | 0/10 | 0/10 | not_run | `reports/fveval/fveval_subset_eval_summary_20260511T141418Z.md`; `evaluation/results/fveval_subset_results.md` |
| Design2SVA | 10 | 10/10 | 10/10 | 10/10 | 0/10 | n/a | not_run | `reports/fveval/fveval_subset_eval_summary_20260511T141418Z.md`; `evaluation/results/fveval_subset_results.md` |

This is not an official FVEval reproduction. It does not run JasperGold, Codex,
Qwen, or FVEval's commercial property-equivalence flow. The 30/30 fallback rate
means no external predictions were provided, not LLM performance.

## Table 9. Local Qwen Subset

| Evidence point | Value | Boundary | Source report(s) |
| --- | --- | --- | --- |
| Model | `Qwen/Qwen3-14B-AWQ` | Local endpoint only | `reports/local_llm/qwen_workflow_subset_summary_20260511T202620Z.md`; `reports/local_llm/qwen_runtime_fix_summary_20260511T202643Z.md` |
| Backend | local vLLM | OpenAI-compatible local endpoint at `http://127.0.0.1:8000/v1` | `reports/local_llm/qwen_workflow_subset_summary_20260511T202620Z.md`; `reports/local_llm/qwen_runtime_fix_summary_20260511T202643Z.md` |
| Case count | 9 | 3 SVA repair, 3 triage, 3 coverage | `reports/local_llm/qwen_workflow_subset_summary_20260511T202620Z.md` |
| Status | `ok` | Workflow subset completed | `reports/local_llm/qwen_workflow_subset_summary_20260511T202620Z.md` |
| Valid JSON | `True` | Strict JSON/schema handling evidence | `reports/local_llm/qwen_workflow_subset_summary_20260511T202620Z.md` |
| Fallback count | 0 | No deterministic or cloud fallback used | `reports/local_llm/qwen_workflow_subset_summary_20260511T202620Z.md` |
| LLM error count | 0 | No local model errors recorded in subset | `reports/local_llm/qwen_workflow_subset_summary_20260511T202620Z.md` |
| `LOCAL_ONLY` | `True` | Local-only execution policy enabled | `reports/local_llm/qwen_workflow_subset_summary_20260511T202620Z.md`; `reports/local_llm/qwen_runtime_fix_summary_20260511T202643Z.md` |
| Cloud fallback allowed | `False` | No cloud fallback permitted | `reports/local_llm/qwen_workflow_subset_summary_20260511T202620Z.md`; `reports/local_llm/qwen_runtime_fix_summary_20260511T202643Z.md` |
| Cloud fallback called | `False` | No cloud fallback called | `reports/local_llm/qwen_workflow_subset_summary_20260511T202620Z.md`; `reports/local_llm/qwen_runtime_fix_summary_20260511T202643Z.md` |
| Latency total | 15597.22 ms | Readiness subset latency only, not a comparative benchmark | `reports/local_llm/qwen_runtime_fix_summary_20260511T202643Z.md` |

The Qwen 3+3+3 subset is not a full Qwen benchmark and does not support a
Qwen-vs-Codex comparison.

## Table 10. Workflow And CLI Capability

| Capability | Evidence | External-call boundary | Source report(s) |
| --- | --- | --- | --- |
| Unified CLI | `jasperloop` commands exist for `build-packet`, `repair`, `triage`, `coverage`, `eval`, `moore-handoff`, and workflow demo | Stage 5A CLI records manifests and planned commands; dry-run does not call Codex, Qwen, JasperGold, Moore, or cloud models | `docs/cli_usage.md`; `reports/release/stage5_result_ledger_20260511T205601Z.md` |
| Workflow wrapper | `python -m app.cli workflow repair --dry-run` passed and emitted workflow artifacts | Dry-run stayed local with `external_send_allowed=false` | `docs/workflow_usage.md`; `reports/workflows/workflow_smoke_summary_20260511T182158Z.md` |
| Moore handoff automation | CLI/workflow can prepare/validate/import sanitized verifier outcomes | No raw Jasper logs, trace directories, generated harness dumps, or license output are committed | `reports/release/stage5_result_ledger_20260511T205601Z.md`; `docs/e2e_demo.md` |
| Replay end-to-end demo | Replay workflow demo emitted problem spec, repair candidate, Moore handoff manifest, imported verifier outcome, intent alignment result, and report | Does not call Codex, Qwen, JasperGold, Moore, network, or cloud services | `reports/workflows/e2e_demo_summary_20260511T191259Z.md`; `docs/e2e_demo.md` |
| Intent alignment evaluator | Static/offline evaluator produced 18 smoke results with labels and manual-review flags | Heuristic review only, not formal equivalence and not a substitute for engineer review | `docs/intent_alignment.md`; `reports/alignment/intent_alignment_smoke_summary_20260511T180423Z.md` |
| Local Qwen workflow backend | Local endpoint route completed a 9-case 3+3+3 subset | `LOCAL_ONLY=true`, no cloud fallback, not a full benchmark | `docs/local_qwen_workflow.md`; `reports/local_llm/qwen_workflow_subset_summary_20260511T202620Z.md` |
| Playbook guidance integration | Prompts/workflow dry-runs reference DV playbooks and rule libraries | Guidance assets only, not new experiment evidence | `reports/release/stage55_result_ledger_20260511T224417Z.md`; `reports/skills/skill_integration_gate_20260511T214452Z.md` |

## Table 11. Claim Boundary

| Claim area | Supported statement | Unsupported statement | Source report(s) |
| --- | --- | --- | --- |
| Jasper proof | JasperGold/Moore proof outcomes are verifier evidence for the checked properties under the checked assumptions | A proof pass does not imply intent alignment or that the property captures the intended requirement | `reports/jasper/codex_repair_final_proof_summary_20260511T053413Z.md`; `reports/jasper/sva_repair_ablation_final_proof_summary_20260511T143254Z.md`; `docs/intent_alignment.md` |
| Vacuity | Reports can state "not parsed as vacuous" or "not flagged vacuous" where that is what the manifest records | `not_flagged_vacuous` is not explicit non-vacuity certification when `jasper_vacuity_status` is null or explicit vacuity flow did not run | `reports/jasper/codex_repair_final_proof_summary_20260511T053413Z.md`; `reports/jasper/sva_repair_ablation_final_proof_summary_20260511T143254Z.md`; `reports/jasper/expanded_benchmark_evidence_summary_20260511T064639Z.md` |
| Best-of-k | pass@k is an upper-bound search result over available candidates | Best-of-k is not single-output success | `reports/jasper/codex_repair_final_proof_summary_20260511T053413Z.md`; `reports/repair/sva_repair_ablation_summary_20260511T064252Z.md`; `docs/workflow_usage.md` |
| Codex benchmark | Codex full benchmark measured 57 cases with 71/71 valid JSON and task-specific scaffold/triage/coverage metrics | Codex full benchmark is not production readiness and did not include Qwen comparison | `reports/llm/codex_full_summary_20260511T015713Z.md` |
| Qwen subset | Local Qwen endpoint completed a 9-case 3+3+3 workflow subset with valid JSON and no fallback | Qwen 3+3+3 is not a full Qwen benchmark and not a Qwen-vs-Codex comparison | `reports/local_llm/qwen_workflow_subset_summary_20260511T202620Z.md`; `reports/local_llm/qwen_runtime_fix_summary_20260511T202643Z.md`; `docs/local_qwen_workflow.md` |
| FVEval-compatible subset | Local 30-case FVEval-compatible subset runner completed with deterministic fallback and no answer leakage | This is not official FVEval reproduction and does not reproduce commercial equivalence or JasperGold proof flow | `reports/fveval/fveval_subset_eval_summary_20260511T141418Z.md`; `reports/benchmarks/fveval_subset_import_20260511T031107Z.md` |
| Workflow/demo | CLI and replay workflow evidence show local plumbing, manifests, handoff boundaries, and static alignment integration | Replay and dry-run evidence is not real model performance and not a new JasperGold/Moore result | `reports/workflows/workflow_smoke_summary_20260511T182158Z.md`; `reports/workflows/e2e_demo_summary_20260511T191259Z.md`; `docs/e2e_demo.md` |
| Project readiness | JasperLoop-DV is a research prototype and workflow scaffold for formal-aware DV assistance | The project is not production-ready signoff automation | `reports/release/stage5_result_ledger_20260511T205601Z.md`; `reports/research/stage55_to_stage6_entry_plan_20260511T224417Z.md`; `docs/design_doc.md` |
