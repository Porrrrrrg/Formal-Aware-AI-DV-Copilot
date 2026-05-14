# Design2SVA Jasper Subset Error Analysis

## Scope

This note analyzes the Stage 6 Design2SVA subset on three local fixture cases with `k=3`.

- LLM-only artifact: `evaluation/results/design2sva_eval_codex_subset.json`
- JasperGold-checked artifact: `evaluation/results/design2sva_eval_codex_jasper_subset.json`
- Summary table: `evaluation/results/design2sva_results.md`

Moore did not send new external prompts. It replayed the already-generated Codex candidates through `copilot/llm_adapters/replay_json.py` and used JasperGold as the formal oracle.

## Result Summary

| Run | Formal | valid_json_rate | fallback_rate | hallucinated_signal_rate | syntax@1 | syntax@k | proven@1 | proven@k | non_vacuous@k | Source |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| Codex subset | not_run | 1.000 | 0.000 | 0.000 | 1.000 | 1.000 | 0.000 | 0.000 | 0.000 | llm=9 |
| Codex + JasperGold subset | measured | 1.000 | 0.000 | 0.000 | 1.000 | 1.000 | 0.000 | 0.000 | 0.000 | llm=9 |

The LLM-only run looked clean because all nine initial Codex candidates were schema-valid, used visible/retrieved signals, avoided fallback, and passed the local SVA syntax scaffold. That is useful infrastructure evidence: the evaluator can route real Codex output into a typed Design2SVA result artifact without JSON repair or deterministic substitution.

JasperGold changed the interpretation. With formal checking enabled, all 18 checked rows, including initial candidates and one repair round per candidate, returned `proof_status=unreachable`. The evaluator now classifies those rows as `weak_vacuous_assertion`, not as formal passes.

## Failure Interpretation

`unreachable` means the relevant property target is not reached under the generated harness, assumptions, reset behavior, antecedent, or proof setup. In this context it is evidence that the assertion is not formally useful yet. The assertion may be syntactically valid and may reference only real signals, but it still fails to establish a meaningful non-vacuous proof objective.

The key distinction is:

- `syntax@k=1.000` says at least one candidate per case is parseable and locally well-formed.
- `valid_json_rate=1.000` says the hosted model respected the structured output contract.
- `hallucinated_signal_rate=0.000` says the candidates stayed inside the visible/retrieved signal set.
- `proven@k=0.000` and `non_vacuous@k=0.000` say none of those candidates produced a useful JasperGold proof.

This is why syntax pass is not enough for Design2SVA. It can overstate quality unless every row is tied to formal proof and vacuity status.

## Evaluator Fix

The Stage 6 run exposed a metrics bug: `unreachable` and `uncovered` formal outcomes could fall through as `passed` in the failure-category classifier. The evaluator now maps those proof statuses to `weak_vacuous_assertion`.

The regression test `test_unreachable_formal_result_is_not_counted_as_passed` verifies that an `unreachable` JasperGold result is not counted by `row_success(..., formal_mode=True)`.

## Likely Causes

The current fixture results do not prove which root cause dominates, but the failure mode points to these likely targets:

- Antecedents may be too narrow or unreachable under the formal assumptions.
- The generated property may encode the visible intent but not match a reachable design transaction.
- Harness/reset setup may make the sampled scenario unreachable in the bounded proof context.
- The repair loop currently falls back toward reference-like syntax instead of using `unreachable` as first-class feedback.
- The evaluator checks assertion syntax and proof status, but it does not yet require a cover-before-assert reachability check for the antecedent.

## Next Engineering Steps

The next stage should focus on formal usefulness, not scale.

1. Add antecedent reachability checks before treating a candidate as a useful assertion.
2. Generate a companion cover property for each assertion antecedent and report cover status separately.
3. Feed `unreachable`, `vacuous`, and `uncovered` statuses into the repair prompt as distinct feedback.
4. Add prompt constraints that require the antecedent to describe a reachable transaction from retrieved RTL state and assumptions.
5. Surface harness and reset assumptions in the Design2SVA context builder so the model can avoid impossible setup conditions.
6. Split metrics into initial LLM candidate quality and post-repair formal quality so local repair does not obscure model behavior.

## Claim Boundary

Supported:

- JasperLoop-DV can generate real Codex Design2SVA candidates with clean JSON provenance.
- The Stage 6 pipeline can evaluate those candidates with JasperGold on Moore.
- The current Design2SVA subset shows that schema-clean, syntax-clean, hallucination-free candidates can still be formally useless.
- The evaluator now prevents `unreachable` and `uncovered` formal outcomes from being counted as passes.

Unsupported:

- ProofLoop-level performance.
- Production signoff capability.
- Successful Design2SVA formal assertion generation on this subset.
- Any claim that syntax pass or JSON validity implies functional/formal correctness.
