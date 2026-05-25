# Real LLM Error Analysis

Date: 2026-05-23

Scope: local Qwen backend healthcheck, 3+3+3 subset gate, full local Qwen benchmark, and JasperGold-backed SVA repair re-check after the Codex CLI subprocess route failed.

## Summary

The Codex CLI route did not reach model execution. The Windows app package `codex.exe` still fails from Python subprocess with:

```text
permission_denied: cannot execute Codex executable from subprocess: [WinError 5] Access is denied
```

The generic backend route did reach a real local model. `JASPERLOOP_LLM_CMD` pointed to `python D:\AI-DV\qwen_json_backend.py`, which called a local vLLM OpenAI-compatible endpoint serving `Qwen/Qwen3-14B-AWQ` at `http://127.0.0.1:8000/v1`. The backend doctor and contract test passed.

The first 3+3+3 subset run exposed failure-triage output-control problems: JSON validity 0.667, fallback rate 0.333, and hallucinated signal rate 0.333. The triage prompt, first-JSON extraction, and allowed-signal normalization were tightened, then the subset gate was rerun. The rerun passed the subset mechanics: triage JSON validity 1.000, fallback rate 0.000, and hallucinated signal rate 0.000.

The follow-up full local Qwen benchmark used the same backend route and completed SVA repair, structured failure triage, and structured coverage closure. The saved Qwen SVA repair outputs were then copied to Moore and re-checked with JasperGold. This is still not Codex CLI performance, official FVEval performance, or production signoff.

## Subset Metrics

| Task | Cases | Valid JSON | LLM Success | Fallback | LLM Error | Hallucinated Signals | Task Metric |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| SVA repair | 3 | 1.000 | 1.000 | 0.000 | 0.000 | 0.000 | final exact match 0.667 |
| Failure triage | 3 | 1.000 | 1.000 | 0.000 | 0.000 | 0.000 | issue/action 0.667/0.667 |
| Coverage closure | 3 | 1.000 | 1.000 | 0.000 | 0.000 | n/a | gap/action 1.000/1.000 |

## Full Local Qwen Metrics

| Task | Cases | Valid JSON | LLM Success | Fallback | LLM Error | Hallucinated Signals | Task Metric |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| SVA repair | 23 | 1.000 | 1.000 | 0.000 | 0.000 | 0.043 | final exact match / repair success 0.913 |
| Failure triage | 53 | 0.981 | 0.981 | 0.019 | 0.019 | 0.000 | issue/action 0.811/0.811 |
| Coverage closure | 14 | 1.000 | 1.000 | 0.000 | 0.000 | n/a | gap/action 1.000/1.000 |

The full local Qwen run passed the output mechanics gate: JSON validity >= 0.90, fallback rate <= 0.25, and hallucinated signal rate <= 0.10 where measured. This is a gate result, not formal signoff.

## Full Local Qwen Triage Rerun After Assumption/Vacuity Improvement

Date: 2026-05-25.

After v1.1.5 added structured assumption/vacuity triage cues, the full 53-case local Qwen triage benchmark was rerun with the same generic backend route:

```text
JASPERLOOP_LLM_CMD=python D:\AI-DV\qwen_json_backend.py
LOCAL_BASE_URL=http://127.0.0.1:8000/v1
SERVED_MODEL_NAME=Qwen/Qwen3-14B-AWQ
```

This rerun did not include SVA repair, coverage closure, Codex CLI, or JasperGold. Raw JSON stayed local and ignored.

| Triage run | Cases | Valid JSON | LLM Success | Fallback | LLM Error | Hallucinated Signals | Issue/Action |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| v1.1.2 full local Qwen | 53 | 0.981 | 0.981 | 0.019 | 0.019 | 0.000 | 0.811 / 0.811 |
| v1.1.5 after-triage rerun | 53 | 1.000 | 1.000 | 0.000 | 0.000 | 0.000 | 0.962 / 0.962 |

The scoped assumption/vacuity improvement transferred to the full triage setting: gold `assumption_constraint_bug` cases improved from 3/12 to 12/12. The corrected cases were `apb_C11`, `apb_C2`, `apb_C7`, `arbiter_A11`, `arbiter_A6`, `arbiter_A7`, `fifo_D10`, `rv_B6`, and `rv_B7`.

The main side effect was a one-case regression in `testbench_stimulus_bug`: `rv_B8` changed from the correct `testbench_stimulus_bug` / `fix_testbench_or_stimulus` classification to `reachable_coverage_gap` / `add_directed_test_or_sequence`. The pre-existing `fifo_D17` stimulus miss remained. These two misses suggest that the next triage iteration should focus on distinguishing stimulus incompleteness from reachable coverage closure opportunities.

## Stimulus-vs-Coverage Scoped Triage Gate

Date: 2026-05-25.

The follow-up scoped task added derived `stimulus_context` cues and prompt guidance for separating existing stimulus/testbench incompleteness from true reachable coverage closure. It did not change benchmark labels, rerun SVA repair or coverage closure, run JasperGold, or claim Codex CLI performance.

Structured fallback regression with rebuilt packets reached 53/53 issue/action agreement. The target guardrails were `testbench_stimulus_bug` 4/4, `reachable_coverage_gap` 9/9, `unreachable_or_invalid_coverage_goal` 5/5, and `assumption_constraint_bug` 12/12.

The real local Qwen scoped gate covered all 18 stimulus/coverage/invalid triage cases. It produced valid JSON 1.000, fallback 0.000, LLM error 0.000, hallucinated signal 0.000, and issue/action accuracy 18/18. The two known misses were corrected: `rv_B8` and `fifo_D17` both classified as `testbench_stimulus_bug` with `fix_testbench_or_stimulus`.

This is a scoped local Qwen result, not a full benchmark rerun. The next validation step is a separate full local Qwen triage rerun to check transfer and non-target-label regressions.

## Full Local Qwen Triage Rerun After Stimulus-vs-Coverage Improvement

Date: 2026-05-25.

After v1.1.7 added structured stimulus-vs-coverage cues, the full 53-case local Qwen triage benchmark was rerun with the same generic backend route:

```text
JASPERLOOP_LLM_CMD=python D:\AI-DV\qwen_json_backend.py
LOCAL_BASE_URL=http://127.0.0.1:8000/v1
SERVED_MODEL_NAME=Qwen/Qwen3-14B-AWQ
```

This rerun did not include SVA repair, coverage closure, Codex CLI, or JasperGold. Raw JSON stayed local and ignored.

| Triage run | Cases | Valid JSON | LLM Success | Fallback | LLM Error | Hallucinated Signals | Issue/Action |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| v1.1.2 full local Qwen | 53 | 0.981 | 0.981 | 0.019 | 0.019 | 0.000 | 0.811 / 0.811 |
| v1.1.6 after assumption/vacuity rerun | 53 | 1.000 | 1.000 | 0.000 | 0.000 | 0.000 | 0.962 / 0.962 |
| v1.1.7 after stimulus-vs-coverage rerun | 53 | 1.000 | 1.000 | 0.000 | 0.000 | 0.000 | 1.000 / 1.000 |

The scoped stimulus-vs-coverage improvement transferred to the full triage setting. `rv_B8` and `fifo_D17` remained fixed as `testbench_stimulus_bug` / `fix_testbench_or_stimulus`, while `reachable_coverage_gap` stayed at 9/9 and `unreachable_or_invalid_coverage_goal` stayed at 5/5. The previous assumption/vacuity improvement also held: `assumption_constraint_bug` remained 12/12.

No new non-target regressions were observed in this rerun. The result supports the current structured evidence, prompt, and normalization pipeline for the 53-case local triage benchmark, but it is still not Codex CLI performance, JasperGold-backed triage validation, official FVEval performance, or production signoff.

## JasperGold Re-check Metrics

Source checkpoint: `v1.1.2-local-qwen-full-benchmark`.

Environment: `moore.wot.ece.northwestern.edu` with `JASPER_BIN=/vol/cadence2018/XCELIUM1809/tools.lnx86/jasper/bin/jg`.

Raw Qwen artifact: `artifacts/qwen_jasper_recheck/sva_repair_qwen_full.json`.

| Scope | Candidates | Syntax Pass | Proven | Falsified | Undetermined | Vacuous | Not Flagged Vacuous |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Local Qwen SVA repair final candidates | 23 | 22/23 | 22 | 0 | 0 | 0 | 23 |

The single syntax failure was `repair_fifo_reset_wrong_polarity`, where the local Qwen full-run report had already identified a hallucinated signal, `out_valid`. JasperGold did not produce proof/vacuity status for that candidate.

One candidate, `repair_arbiter_single_req1_wrong_grant`, proved under JasperGold even though it did not match the local exact template. This is the clearest example that JasperGold proof and exact-template intent alignment are related but separate metrics.

## Error Categories

1. JSON/schema failures: fixed for the subset rerun. The initial `apb_C5` response included extra prompt/evidence text after JSON-like content; first-valid-JSON extraction now prevents this from becoming a fallback when a valid object is present.
2. Hallucinated signals: fixed for the subset rerun and controlled in full triage. Full SVA repair still reported one hallucinated signal, `out_valid`, in `repair_fifo_reset_wrong_polarity`; JasperGold re-check reported this candidate as a syntax failure.
3. Wrong issue type: historical v1.1.2 issue. The original full triage run systematically under-detected assumption/constraint bugs, often classifying them as `assertion_property_bug`; the v1.1.6 and v1.1.7 reruns corrected this class in the local Qwen benchmark.
4. Wrong recommended action: historical v1.1.2 issue. The corresponding wrong action was usually `fix_assertion_property` instead of `fix_assumption_constraint`; the v1.1.6 and v1.1.7 reruns corrected these actions for the tracked assumption/constraint cases.
5. Syntactically valid but intent-wrong SVA: SVA repair produced valid JSON and no fallback, but `repair_arbiter_single_req1_wrong_grant` and `repair_fifo_reset_wrong_polarity` did not reach scaffold exact match after 3 rounds.
6. Property proves but is too weak: `repair_arbiter_single_req1_wrong_grant` proved under JasperGold despite failing exact-template match, so it needs human intent review rather than automatic acceptance.
7. Vacuity or overconstraint cases: historical v1.1.2 weakness. Full triage originally classified only 3 of 12 gold assumption/constraint cases, but the post-v1.1.5 full reruns classified 12/12.
8. Coverage goal incorrectly treated as reachable: not observed in the full coverage run. In triage, v1.1.6 still confused `rv_B8` and `fifo_D17` stimulus bugs with reachable coverage gaps; the v1.1.7 full rerun corrected both while preserving 9/9 `reachable_coverage_gap` and 5/5 `unreachable_or_invalid_coverage_goal`.
9. Raw-log vs structured LLM comparison: not run; only structured subset paths were evaluated.
10. JasperGold feedback helped repair: not evaluated as an iterative repair loop in this run. JasperGold was used as a post-hoc re-check of saved local Qwen final candidates.

## Environment Findings

- `codex`/`codex.exe` resolves to the Codex Windows app package, but cannot be launched from this subprocess environment.
- `python scripts/doctor_llm_backend.py --json` confirms the executable exists and its parent directory can be listed, but both `codex.exe --version` and the JSON backend contract classify as `permission_denied`.
- `python scripts/test_llm_backend_contract.py` passed after switching to `JASPERLOOP_LLM_CMD=python D:\AI-DV\qwen_json_backend.py`.
- Local Qwen healthcheck at `http://127.0.0.1:8000/v1` passed through the generic command backend.
- `JASPER_BIN` and `JASPER_ENV` were unset, and no `jg` executable was found.

## Next Step

The local Qwen triage path now has two focused improvement chains: assumption/vacuity triage and stimulus-vs-coverage triage both transferred from scoped gates to the full 53-case rerun. The next experiment should be a deliberate ablation or formal-evidence expansion rather than another broad prompt edit. Useful directions are separating the contributions of derived evidence cues, prompt wording, and normalization, or running JasperGold-backed checks for SVA generation if a saved Qwen SVA generation artifact is produced.

Recommended next constraints:

- Keep reporting JSON validity, fallback rate, hallucinated signal rate, and task accuracy separately.
- Do not treat local LLM output mechanics as proof of intent correctness.
- Do not treat JasperGold proof as full semantic intent equivalence.
- If Codex CLI performance is required, set `CODEX_BIN` to a real subprocess-callable CLI binary rather than the Windows app package alias.

The main residual risk is no longer backend invocation for the local Qwen route; it is whether the current evidence/prompt/normalization improvements generalize beyond the current 53-case triage benchmark.
