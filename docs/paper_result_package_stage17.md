# Stage 17 Paper Result Package

This package summarizes the current JasperLoop-DV and Design2SVA evidence for a
paper-style results section. It does not add new experiments, send new model
prompts, rerun JasperGold, relabel benchmarks, or claim production signoff.

The strongest new Design2SVA claim after Stage 16 is bounded: on the local
12-case fixture set, with native and wrapper oracle gates passing first, real
Codex candidates evaluated through the repaired JasperGold wrapper reached
`proven_non_vacuous@k = 1.000` for `k = 3`. This is local benchmark evidence,
not an official FVEval reproduction and not broad industrial generalization.

## Result Narrative

Formal-aware agent evaluation needs wrapper parity because a generated assertion
is only meaningful under the harness actually used to check it. Earlier
Design2SVA stages showed the failure mode directly: native benchmark references
proved, while the same reference assertions failed after embedding through the
Design2SVA wrapper. That native-proves/wrapper-fails split means candidate
quality was not isolated. The repaired wrapper therefore became an evaluation
gate, not a convenience detail.

Reachability is the second gate. Schema-valid JSON and syntax-clean SVA can
still be useless if the antecedent never triggers, reset never releases, or a
cover goal is unreachable under the benchmark assumptions. The evaluation
therefore separates syntax, signal validity, reset/clock contracts, companion
covers, vacuity checks, and proof status before a row can be counted as useful
formal evidence.

JasperGold feedback is the third gate. The LLM proposes candidates; JasperGold
or replayed JasperGold results classify proof, vacuity, cover reachability,
counterexample, and tool-status outcomes. That feedback is what turns a fluent
candidate into a measured artifact, and it is what lets repair loops distinguish
candidate errors from wrapper, harness, and oracle errors.

## Table 1. Project Stages And What Each Proved

Here "proved" means established by the scoped repository evidence, not
production verification signoff.

| Stage | Scope | What it proved or established | Boundary |
| --- | --- | --- | --- |
| Stage 2 | Initial Moore/JasperGold packets, Codex runs, schema hardening | 30 primary local-DV packets had Jasper report and trace references; the later Codex full benchmark recorded 57 attempted cases and 71/71 valid JSON outputs | Early benchmark and schema evidence, not deployment readiness |
| Stage 3 | Baseline release, repair-output restore, final-proof handoff, FVEval-compatible import | Restored Codex SVA repair candidates were checked on Moore/JasperGold with 34/34 syntax pass and 34/34 proven | Proof is scoped to checked harnesses; FVEval subset is local-compatible scaffolding only |
| Stage 4 | Expanded evidence, FVEval-compatible subset evaluation, SVA repair ablation | Expanded local-DV benchmark reached 53/53 schema-valid prove-backed packets; SVA repair ablation handoff reached 126/126 syntax pass and proven on Moore/JasperGold | Some auxiliary cover/vacuity paths were blocked; proof does not imply intent alignment |
| Stage 5 / 5.5 | CLI, workflow packaging, Moore handoff, local Qwen path, skills/playbooks | The project gained repeatable workflow surfaces, dry-run manifests, local replay demo, static intent alignment, and local-model plumbing | Workflow and skills are integration evidence, not correctness evidence |
| Design2SVA Stage 5 | Retrieval-assisted Design2SVA evaluator | The repo gained case schemas, RTL/harness retrieval context, pass@k metrics, replay modes, and optional JasperGold checking | Dry-run/replay rows validate infrastructure only |
| Design2SVA Stage 6-7 | First Jasper subset and anti-vacuity direction | Syntax-clean, schema-valid Codex candidates could still fail as weak/vacuous or unreachable under JasperGold | Negative result; no broad Design2SVA success claim |
| Design2SVA Stage 10-11 | Reference and native-oracle root-cause ladder | Native references proved 3/3 while wrapper-embedded references failed, isolating wrapper/embedding as the immediate confound | Candidate generation quality was not yet isolated |
| Design2SVA Stage 12-13 | Wrapper parity repair and fixed-wrapper rerun | Repaired wrapper matched native reference behavior on measured fixtures; prior committed Codex candidates proved non-vacuously on the three-case fixed-wrapper reruns | No new prompts in Stage 13; only a measured local subset |
| Design2SVA Stage 14 | Error taxonomy and ablation plan | Failure categories and root-cause axes were separated so syntax, reachability, wrapper, oracle, and candidate errors are not conflated | Planning/taxonomy artifact unless a row records measured JasperGold status |
| Design2SVA Stage 15 | Expanded 12-case oracle gate | Native references proved 12/12; wrapper reference oracle proved 12/12 non-vacuously with wrapper parity passing | Oracle/harness validity evidence, not LLM generation evidence |
| Design2SVA Stage 16 | Expanded real Codex Design2SVA run | Real Codex generated 36/36 schema-valid, syntax-valid, non-fallback candidates; JasperGold replay reached `proven@1 = 0.750` and `proven_non_vacuous@k = 1.000` for `k = 3` on 12 local cases | Local fixture result; component attribution still needs matched ablations |
| Stage 17 | Paper result packaging | Consolidates the bounded result story, tables, taxonomy, and figure plan | No new experiment or source-code claim |

## Table 2. Design2SVA 12-Case Result

| Evidence row | Cases | k | Key metrics | Interpretation | Source artifact |
| --- | ---: | ---: | --- | --- | --- |
| Native oracle gate | 12 | N/A | `native_reference_proven_rate = 1.000`; native vacuity not measured in that path | The fixture references prove in the native benchmark flow | `evaluation/results/design2sva_native_oracle_expanded_jasper.json` |
| Wrapper reference oracle gate | 12 | 1 | `reference_proven@1 = 1.000`; `reference_non_vacuous@1 = 1.000`; `wrapper_parity_pass_rate = 1.000` | The repaired Design2SVA wrapper preserves the reference behavior for this local set | `evaluation/results/design2sva_reference_oracle_expanded_jasper.json` |
| Real Codex generation, before JasperGold | 12 | 3 | 36/36 real LLM outputs; `valid_json_rate = 1.000`; `syntax@k = 1.000`; `fallback_rate = 0.000`; `hallucinated_signal_rate = 0.000`; formal status `not_run` | Structured output quality is clean, but no proof claim comes from this row alone | `evaluation/results/design2sva_eval_codex_expanded_subset.json` |
| JasperGold replay of exact Codex candidates | 12 | 3 | `proven@1 = 0.750`; `proven@k = 1.000`; `non_vacuous@k = 1.000`; `proven_non_vacuous@k = 1.000`; `antecedent_reachable@k = 1.000` | 9/12 cases pass at first candidate; 12/12 have at least one proven non-vacuous candidate among three | `evaluation/results/design2sva_eval_codex_expanded_jasper.json` |
| Diagnostic counts | 12 | 3 | Final rows: `proven_non_vacuous=36`; intermediate diagnostics: `unreachable_cover_goal=7`; `cover_generation_bug=7` | Intermediate cover diagnostics are kept separate from final pass@k success | `evaluation/results/design2sva_eval_codex_expanded_jasper.json` |

## Table 3. Ablation Summary

The Stage 17 ablation ledger is generated by
`evaluation/run_design2sva_ablation.py` from committed artifacts only.
Unmeasured component rows are marked `not_run`; they are not reported as zero.

| Stage 17 row | Evidence status | Cases | k | Key result | Source artifact |
| --- | --- | ---: | ---: | --- | --- |
| `reference_oracle` | JasperGold measured control | 12 | 1 | Wrapper reference oracle: `proven_non_vacuous@k = 1.000`, `wrapper_parity_pass_rate = 1.000` | `evaluation/results/design2sva_reference_oracle_expanded_jasper.json` |
| `native_oracle` | JasperGold measured native control | 12 | 1 | Native references prove 12/12; native vacuity is not measured in this path | `evaluation/results/design2sva_native_oracle_expanded_jasper.json` |
| `codex_design2sva_current` | JasperGold-measured replay of real Codex candidates | 12 | 3 | `valid_json_rate = 1.000`, `proven@1 = 0.750`, `proven_non_vacuous@k = 1.000` | `evaluation/results/design2sva_eval_codex_expanded_jasper.json` |
| `codex_fixed_wrapper_rerun` | JasperGold measured replay | 3 | 3 | Fixed-wrapper rerun reaches `proven_non_vacuous@k = 1.000` | `evaluation/results/design2sva_eval_codex_fixed_wrapper_rerun.json` |
| `codex_antivacuity_current` | JasperGold measured replay | 3 | 5 | Anti-vacuity fixed-wrapper rerun reaches `proven_non_vacuous@k = 1.000` | `evaluation/results/design2sva_eval_antivacuity_codex_fixed_wrapper_rerun.json` |
| `deterministic_scaffold` | Local scaffold only | 3 | 3 | Schema/syntax plumbing only; formal metrics `not_run` | `evaluation/results/design2sva_eval_local.json` |
| `replay_baseline` | Local replay only | 3 | 3 | Committed Codex replay baseline; formal metrics `not_run` | `evaluation/results/design2sva_codex_replay_expanded_local.json` |
| `direct_prompt_placeholder` | `not_run` | N/A | N/A | Reserved for a gated future external LLM run | none |
| `no_retrieval_placeholder` | `not_run` | N/A | N/A | Reserved for a gated future no-retrieval run | none |
| `no_antivacuity_placeholder` | `not_run` | N/A | N/A | Reserved for a gated future no-anti-vacuity run | none |

Earlier ablation and diagnostic controls remain useful background, but they
must not be collapsed with the Stage 17 Design2SVA ledger:

| Ablation or control | Evidence status | Result | What it isolates | Claim boundary |
| --- | --- | --- | --- | --- |
| Structured packet vs reduced triage packets | Measured local scaffold | Full structured packet issue/action accuracy 0.906; minimal packet 0.434 | Evidence packet fields matter for DV triage scaffolds | Deterministic scaffold, not hosted-model proof |
| Remove assertion manifest | Measured local scaffold | Issue/action accuracy 0.868 vs 0.906 full packet | Assertion intent helps but is not the only signal | Triage metric only |
| Remove assumption manifest | Measured local scaffold | Issue/action accuracy 0.755 | Assumption context affects root-cause/action decisions | Triage metric only |
| Remove coverage plan | Measured local scaffold | Issue/action accuracy 0.604 | Coverage context prevents coverage cases collapsing into assertion-style diagnoses | Triage metric only |
| SVA repair seven-variant ablation | Moore/JasperGold handoff measured | 126/126 handoff candidates syntax-pass and prove | Repair variants can be checked under a common formal handoff | pass@k equals pass@1 for the committed handoff because one final row per case was checked |
| Pre-parity Design2SVA wrapper control | Moore/JasperGold measured on three cases | Native references proved 3/3 while wrapper references failed 0/3 | Wrapper defects can dominate apparent candidate failures | Diagnostic control, not model-quality evidence |
| Fixed-wrapper Design2SVA rerun | Moore/JasperGold measured on three cases | Prior committed Codex candidates reached `proven_non_vacuous@k = 1.000` after wrapper repair | Fair rerun path after removing wrapper confound | No new prompts; three-case subset only |
| Expanded Design2SVA oracle gate | Moore/JasperGold measured on 12 cases | Native 12/12 proven; wrapper 12/12 proven non-vacuous | Candidate failures can be attributed only after oracle and wrapper pass | Local fixture validity gate |
| Expanded Design2SVA real Codex path | Moore/JasperGold replay measured on 12 cases | `proven@1 = 0.750`; `proven_non_vacuous@k = 1.000` for `k = 3` | Full current pipeline result | Does not isolate whether retrieval, reachability guidance, sampling, or repair caused the gain |
| Direct/retrieval/reachability component ablations | Dry-run/replay plan only | Variant schema and metrics exist; no formal component attribution yet | Planned isolation of retrieval context, reachability guidance, and anti-vacuity repair | Do not cite as model performance until measured with real candidates and JasperGold |

## Table 4. Failure Taxonomy

| Class | Axis | Definition | Reporting rule |
| --- | --- | --- | --- |
| `syntax_error` | Candidate | JSON/schema, SVA syntax, or Jasper syntax failure prevents meaningful proof interpretation | Fix structure or syntax before any formal claim |
| `unknown_signal` | Candidate | Candidate references identifiers outside visible or retrieved RTL context | Count separately from proof failure; repair signal grounding |
| `reset_clock_mismatch` | Candidate or wrapper | Clock edge, reset signal, or reset polarity does not match task/native harness contract | Compare emitted SVA against `clock_reset` metadata and native flow |
| `unsupported_helper_code` | Candidate | Candidate emits helper code outside the task policy or wrapper embedding support | Remove helper code or extend the policy before proof |
| `overstrong_assertion` | Candidate | Assertion is reachable and checked but falsified by JasperGold | Use counterexample feedback to weaken or correct semantics |
| `weak_vacuous_assertion` | Candidate | Assertion is syntax-clean but formally weak, vacuous, or unhelpful without a more specific reachability label | Never count as useful formal evidence |
| `unreachable_antecedent` | Candidate reachability | Companion cover for an implication antecedent is unreachable or uncovered | Repair the trigger before judging the consequent |
| `unreachable_cover_goal` | Candidate or diagnostic cover | The generated cover objective is unreachable, uncovered, or invalid for the target check | Debug cover construction, invariant handling, reset, and assumptions |
| `temporal_mismatch` | Candidate semantics | Candidate is structurally valid but differs from expected temporal intent or formal status is unavailable | Use intent, traces, reference feedback, or counterexamples before proof claims |
| `wrapper_embedding_bug` / `design2sva_embedding_bug` | Root cause | Native reference proves but the wrapper-embedded reference fails | Fix wrapper topology, file order, bind path, assumptions, clock/reset, or property focus |
| `native_harness_unreachable` | Root cause | Native benchmark cannot prove or reach its own reference objective | Stop downstream attribution and repair benchmark/harness validity first |
| `proven_non_vacuous` | Positive outcome | Candidate or reference assertion is proven and not flagged vacuous, with required reachability satisfied or no antecedent obligation | Count only when the artifact records measured or replayed JasperGold evidence |

## Suggested Figures

1. Pipeline diagram: `RTL/spec/SVA/assumptions/coverage -> JasperGold or replay -> typed BackendResult -> EvidencePacket + retrieval -> agents -> candidate JSON -> JasperGold feedback -> report`.
2. Evidence packet flow: source artifacts, schema validation, prompt-visible fields, hidden expected labels, candidate output, metric aggregation, and claim boundary.
3. Wrapper parity diagnostic ladder: native reference proof, wrapper reference proof, reset/post-reset cover, candidate antecedent cover, assertion proof/vacuity.
4. pass@k result chart: two bars for the Stage 16 local Design2SVA result, `proven@1 = 0.750` (9/12) and `proven@k = 1.000` for `k = 3` (12/12), annotated as best-of-three local fixture evidence.

## Claim Boundaries

- No production signoff, deployment readiness, or unattended RTL verification is claimed.
- The strongest Design2SVA result is a local 12-case benchmark result.
- The FVEval-compatible infrastructure and local subset are not an official
  FVEval reproduction and do not reproduce FVEval's commercial equivalence flow.
- `valid_json_rate`, `syntax@k`, `proven@k`, reachability, and non-vacuity are
  separate metrics and must not be collapsed into one score.
- `pass@k` is a best-of-k search result, not a guarantee that the first model
  sample is sufficient.
- JasperGold proof is scoped to the checked RTL, harness, assumptions, property,
  bound, and tool setup.
- Intent alignment remains a review question unless separately evaluated by
  expert review, equivalence, or mutation-style tests.

## Source Pointers

- `docs/design2sva_expanded_codex_stage16_error_analysis.md`
- `docs/stage16_claim_update.md`
- `docs/research_claims_after_stage16.md`
- `docs/design2sva_expanded_oracle_stage15.md`
- `docs/design2sva_wrapper_parity_stage12.md`
- `docs/design2sva_fixed_wrapper_rerun_stage13.md`
- `docs/design2sva_error_taxonomy.md`
- `evaluation/results/design2sva_results.md`
- `evaluation/results/design2sva_eval_codex_expanded_jasper.json`
- `evaluation/results/design2sva_reference_oracle_expanded_jasper.json`
- `evaluation/results/ablation_results.md`
