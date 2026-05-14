# Full Codex Benchmark Error Analysis

Date: 2026-05-14
Branch analyzed: `codex/jasperloop-agentic-refactor-v1`

This document analyzes the committed benchmark artifacts currently present on this branch. It separates real Codex LLM outputs from deterministic fallback/scaffold results and intentionally does not claim production readiness, formal signoff, or coverage closure.

## Artifact Scope And Precedence

The branch contains both current raw JSON outputs and older generated report files. The raw JSON artifacts are treated as authoritative for current branch metrics because their case counts differ from the older manifest and summary.

| Artifact | Role | Cases in artifact | Notes |
| --- | --- | ---: | --- |
| `evaluation/results/sva_repair_codex_full.json` | Current raw full Codex SVA repair output | 23 | Real Codex repair proposals; final outcome is scaffold/exact-match, not live Jasper proof. |
| `evaluation/results/agent_eval_codex_full.json` | Current raw full Codex DV triage output | 53 | Real Codex structured diagnosis outputs. |
| `evaluation/results/coverage_eval_codex_full.json` | Current raw full Codex coverage-closure output | 14 | Real Codex structured coverage outputs. |
| `reports/llm/codex_full_manifest_20260511T015713Z.json` | Older generated manifest | 57 | Records 18 SVA, 30 triage, 9 coverage cases and 71 LLM outputs; stale relative to current raw JSON. |
| `reports/llm/codex_full_summary_20260511T015713Z.md` | Older generated summary | 57 | Same stale 18/30/9 summary as manifest. |
| `reports/llm/codex_full_error_cases_20260511T015713Z.md` | Older generated error report | 57 | Lists 7 SVA misses and 2 triage misses; current raw JSON shows 8 SVA misses and 3 triage misses. |
| `evaluation/results/fveval_subset_results.md` | Deterministic fallback subset result | 30 | No Codex, Qwen, or Jasper execution; fallback rate is 100%. |

## Execution Family Separation

| Family | Cases | Outputs | Source counts | valid_json_rate | fallback_rate | real_llm_count | Notes |
| --- | ---: | ---: | --- | ---: | ---: | ---: | --- |
| Current full Codex real LLM run | 90 | 106 | `llm`: 106 | 106/106 = 100.0% | 0/106 = 0.0% | 106 | SVA has more outputs than cases because failed repairs use up to three LLM repair rounds. |
| Deterministic fallback FVEval subset | 30 | 30 | `fallback`: 30, derived from fallback=1.000 | 30/30 = 100.0% | 30/30 = 100.0% | 0 | Local subset runner only; exact/reference match is 0/20 eligible cases. |
| Deterministic scaffold verifier | 23 SVA cases | n/a | No prediction source | n/a | n/a | 0 | SVA repair success is scaffold/exact-match success. The verifier is deterministic, but the repair proposals are real LLM outputs. |

The current full Codex run has no deterministic fallback predictions, no LLM errors, and no schema drift visible in the raw task outputs. The SVA task is still scaffold-evaluated: `proven_final` is 0/23 because no final live Jasper proof was run.

## Aggregate Metrics For Current Full Codex Raw JSON

| Metric | Value |
| --- | ---: |
| Task cases | 90 |
| LLM outputs | 106 |
| valid_json_rate | 106/106 = 100.0% |
| fallback_rate | 0/106 = 0.0% |
| real_llm_count | 106 |
| source_counts | `llm`: 106 |
| LLM error rate | 0/106 = 0.0% |
| hallucinated_signal_rate, checked tasks | 0/76 = 0.0% |
| hallucinated_signal_rate, coverage | Not applicable; coverage artifact has checked count 0 and rate `null`. |

The hallucinated-signal denominator is SVA repair plus DV triage only: 23 + 53 = 76 checked rows. Coverage closure did not run a signal-hallucination check in this artifact.

## Task-Specific Results

| Task | Cases | LLM outputs | Source counts | Accuracy metric | Hallucinated signals | Fallback |
| --- | ---: | ---: | --- | --- | --- | ---: |
| SVA repair | 23 | 39 | `llm`: 39 | 15/23 scaffold repair success = 65.2%; 15/23 final exact match = 65.2%; 0/23 proven final | 0/23 = 0.0% | 0/39 |
| DV triage | 53 | 53 | `llm`: 53 | 50/53 issue type accuracy = 94.3%; 50/53 next action accuracy = 94.3% | 0/53 = 0.0% | 0/53 |
| Coverage closure | 14 | 14 | `llm`: 14 | 14/14 gap type accuracy = 100.0%; 14/14 action accuracy = 100.0% | Not checked | 0/14 |

SVA source count is derived from the repair loop: 15 successful cases used one LLM repair round each, and 8 missed cases used three repair rounds each, for 39 LLM repair outputs total. This matches the counting pattern in the older manifest, where 11 one-round successes plus 7 three-round misses yielded 32 outputs.

## SVA Repair Failure Modes

The current raw SVA artifact has 8 scaffold/exact-match misses. Unknown-signal repairs and reset-polarity repairs all reached scaffold success in this run; failures concentrate in overbroad properties, syntax repairs, and temporal/semantic repairs.

| Case | Bug type | Observed failure mode |
| --- | --- | --- |
| `repair_arbiter_single_req1_wrong_grant` | `temporal_or_semantic_error` | Did not repair single-request grant semantics after three LLM rounds. |
| `repair_arbiter_turn0_missing_condition` | `overbroad_property` | Did not add the needed turn/condition narrowing after three rounds. |
| `repair_arbiter_fairness_too_strong` | `temporal_or_semantic_error` | Failed to relax an over-strong fairness/latency property to the reference behavior. |
| `repair_buffer_reset_syntax` | `syntax_error` | Initial syntax issue was not converted into a scaffold-passing final assertion. |
| `repair_buffer_capture_missing_fire` | `overbroad_property` | Did not add the required handshake/fire guard to narrow the property. |
| `repair_apb_setup_syntax` | `syntax_error` | Syntax repair did not reach scaffold success. |
| `repair_apb_write_wrong_addr` | `temporal_or_semantic_error` | Address/phase semantic correction did not match the reference scaffold. |
| `repair_apb_pready_missing_access` | `overbroad_property` | Repeated an access-phase style repair but still missed the scaffold/reference target. |

Important limitation: these are scaffold misses, not formal failures. Conversely, scaffold passes are not formal proofs. The artifact records `jasper_checked: false` and `proven_final: 0.0`, so the supported claim is only scaffold/exact-match repair behavior.

## DV Triage Failure Modes

The DV triage task produced valid JSON for all 53 cases and had no fallback or hallucinated-signal rows. All three misses share the same class-boundary error: the model classified a testbench stimulus bug as a generic reachable coverage gap and recommended adding a directed sequence instead of fixing the testbench/stimulus issue.

| Case | Design | Gold issue/action | Predicted issue/action |
| --- | --- | --- | --- |
| `arbiter_A8` | `arbiter_rr2` | `testbench_stimulus_bug` / `fix_testbench_or_stimulus` | `reachable_coverage_gap` / `add_directed_test_or_sequence` |
| `fifo_D17` | `fifo_1r1w` | `testbench_stimulus_bug` / `fix_testbench_or_stimulus` | `reachable_coverage_gap` / `add_directed_test_or_sequence` |
| `rv_B8` | `rv_buffer` | `testbench_stimulus_bug` / `fix_testbench_or_stimulus` | `reachable_coverage_gap` / `add_directed_test_or_sequence` |

The supported triage claim is strong label/action accuracy on these curated packets, with a clear weakness at the boundary between an actionable testbench defect and a broader coverage stimulus gap. The artifact does not support automatic root-cause signoff or unattended debug decisions.

## Coverage Closure Failure Modes

The current coverage artifact has no label/action misses: 14/14 gap type and 14/14 recommended action correct. It also reports `wrong_test_suggestion_rate: 0.0` and `reachable_sequence_presence_rate: 1.0`; the 9 reachable goals all received directed sequences, while the 5 unreachable/invalid goals did not receive directed tests. The unsupported recommendation rate is 0/14: every `recommended_next_action` is one of the schema-supported actions (`add_directed_test_or_sequence`, `prove_unreachable_or_waive_coverage_goal`, or `fix_assumption_constraint`).

For grounding, all 9 reachable-goal predictions include both a non-empty directed sequence and non-empty evidence list. This is evidence-text grounding against the packet metadata and coverage context, not executable grounding: the generated sequences were not compiled, simulated, or checked against a formal witness in this run.

The absence of observed misses does not imply production coverage closure. The benchmark checks classification and structured recommendations only. It does not compile or execute generated sequences, does not prove unreachable goals, does not apply waivers, and does not run a hallucinated-signal check for coverage outputs.

The main residual coverage risk is overreliance on structured coverage metadata in the evidence packet. The result supports that Codex can classify these curated closure packets and choose the expected next action; it does not support a claim that Codex can independently close coverage or sign off unreachable goals.

## Deterministic Fallback Result

`evaluation/results/fveval_subset_results.md` is not part of the real Codex full run. It reports a deterministic local FVEval-compatible subset runner:

| Metric | Value |
| --- | ---: |
| Cases | 30 |
| valid_json_rate | 30/30 = 100.0% |
| fallback_rate | 30/30 = 100.0% |
| syntax pass | 30/30 = 100.0% |
| exact/reference match | 0/20 eligible = 0.0% |
| hallucinated_signal_rate | 0/30 = 0.0% |
| Jasper | not run |
| Codex/Qwen | not run |

This supports only that the deterministic fallback path emits parseable, syntactically scaffolded JSON for the subset. It does not support any real LLM capability claim.

## Supported Claims

The current branch artifacts support these claims:

- Codex produced schema-valid JSON for all current full-run LLM outputs: 106/106.
- The current full Codex raw outputs used real LLM sources only: `source_counts` is `llm: 106`, with 0 fallbacks and 0 LLM errors.
- SVA repair reached scaffold/exact-match success on 15/23 cases and did not introduce checked hallucinated signals in the final rows.
- DV triage reached 50/53 issue-type accuracy and 50/53 next-action accuracy, with errors concentrated in testbench-stimulus versus reachable-coverage-gap distinctions.
- Coverage closure reached 14/14 gap/action accuracy on the current curated artifact, with reachable sequences present for all reachable goals.
- The deterministic FVEval subset fallback is parseable and syntactically scaffolded, but exact/reference match is 0/20 eligible and no LLM was used.

## Unsupported Claims

The artifacts do not support these claims:

- Production readiness, signoff capability, or unattended deployment.
- Formal proof correctness of SVA repairs. No final live Jasper proof was run.
- Coverage closure signoff. Generated sequences were not compiled or executed, and unreachable goals were not formally proved or waived.
- Official FVEval equivalence or apples-to-apples FVEval results. The local subset runner is deterministic fallback only.
- Qwen comparison. The full Codex manifest explicitly marks Qwen as not run.
- Robustness beyond these curated packets, prompt versions, schemas, and local benchmark labels.
- That the older `reports/llm/codex_full_*` manifest/summary/error-case files describe the current branch raw JSON. They are useful historical generated outputs but are stale relative to the committed raw artifacts.

## Follow-Up Needs

- Regenerate the `reports/llm/codex_full_*` manifest, summary, and error-case report from the current 23/53/14 raw JSON artifacts.
- Add live Jasper proof checks before making any claim about SVA proof success.
- Execute or simulate generated coverage sequences before making any claim about coverage closure.
- Tighten triage labels or prompting around `testbench_stimulus_bug` versus `reachable_coverage_gap`, because every current triage miss is on that boundary.
