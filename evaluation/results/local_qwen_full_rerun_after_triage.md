# Local Qwen Full Triage Rerun After Assumption/Vacuity Improvement

Date: 2026-05-25

Backend: `JASPERLOOP_LLM_CMD=python D:\AI-DV\qwen_json_backend.py`, calling a local vLLM OpenAI-compatible endpoint serving `Qwen/Qwen3-14B-AWQ` at `http://127.0.0.1:8000/v1`.

Result type: real local LLM full triage rerun after the v1.1.5 assumption/vacuity triage improvement. This is not Codex CLI performance, not a full SVA repair or coverage rerun, not JasperGold-backed validation, not deterministic scaffold performance, and not an official FVEval result.

Raw JSON was written locally to `evaluation/results/agent_eval_qwen_full_after_triage.json`. That file remains ignored; this Markdown file is the curated summary intended for version control.

## Gate Metrics

| Run | Cases | Valid JSON | LLM Success | Fallback | LLM Error | Hallucinated Signals | Issue Accuracy | Action Accuracy |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| v1.1.2 full local Qwen triage | 53 | 0.981 | 0.981 | 0.019 | 0.019 | 0.000 | 0.811 | 0.811 |
| v1.1.5 after-triage full rerun | 53 | 1.000 | 1.000 | 0.000 | 0.000 | 0.000 | 0.962 | 0.962 |

Gate decision: the after-triage full rerun passed the local output-mechanics gate. It produced 53/53 real LLM outputs, no deterministic fallback, no JSON failures, and no hallucinated suspect RTL signals.

## Per-Label Accuracy

| Gold issue type | Cases | v1.1.2 issue/action | v1.1.5 issue/action | Change |
| --- | ---: | ---: | ---: | --- |
| `assertion_property_bug` | 12 | 12/12 | 12/12 | no regression |
| `assumption_constraint_bug` | 12 | 3/12 | 12/12 | improved by 9 cases |
| `reachable_coverage_gap` | 9 | 9/9 | 9/9 | no regression |
| `rtl_design_bug` | 11 | 11/11 | 11/11 | no regression |
| `testbench_stimulus_bug` | 4 | 3/4 | 2/4 | regressed by 1 case |
| `unreachable_or_invalid_coverage_goal` | 5 | 5/5 | 5/5 | no regression |

Overall issue/action accuracy improved from 43/53 to 51/53. The improvement is concentrated in gold `assumption_constraint_bug` cases, which moved from 3/12 correct in v1.1.2 to 12/12 correct in this full rerun.

## Changed Cases

The following cases changed from incorrect in v1.1.2 to correct after the assumption/vacuity update:

| Case | Gold issue/action | v1.1.2 prediction | v1.1.5 prediction |
| --- | --- | --- | --- |
| `apb_C11` | `assumption_constraint_bug` / `fix_assumption_constraint` | `assertion_property_bug` / `fix_assertion_property` | `assumption_constraint_bug` / `fix_assumption_constraint` |
| `apb_C2` | `assumption_constraint_bug` / `fix_assumption_constraint` | `assertion_property_bug` / `fix_assertion_property` | `assumption_constraint_bug` / `fix_assumption_constraint` |
| `apb_C7` | `assumption_constraint_bug` / `fix_assumption_constraint` | `assertion_property_bug` / `fix_assertion_property` | `assumption_constraint_bug` / `fix_assumption_constraint` |
| `arbiter_A11` | `assumption_constraint_bug` / `fix_assumption_constraint` | `assertion_property_bug` / `fix_assertion_property` | `assumption_constraint_bug` / `fix_assumption_constraint` |
| `arbiter_A6` | `assumption_constraint_bug` / `fix_assumption_constraint` | `assertion_property_bug` / `fix_assertion_property` | `assumption_constraint_bug` / `fix_assumption_constraint` |
| `arbiter_A7` | `assumption_constraint_bug` / `fix_assumption_constraint` | `assertion_property_bug` / `fix_assertion_property` | `assumption_constraint_bug` / `fix_assumption_constraint` |
| `fifo_D10` | `assumption_constraint_bug` / `fix_assumption_constraint` | `assertion_property_bug` / `fix_assertion_property` | `assumption_constraint_bug` / `fix_assumption_constraint` |
| `rv_B6` | `assumption_constraint_bug` / `fix_assumption_constraint` | `assertion_property_bug` / `fix_assertion_property` | `assumption_constraint_bug` / `fix_assumption_constraint` |
| `rv_B7` | `assumption_constraint_bug` / `fix_assumption_constraint` | `assertion_property_bug` / `fix_assertion_property` | `assumption_constraint_bug` / `fix_assumption_constraint` |

The following case regressed:

| Case | Gold issue/action | v1.1.2 prediction | v1.1.5 prediction | Note |
| --- | --- | --- | --- | --- |
| `rv_B8` | `testbench_stimulus_bug` / `fix_testbench_or_stimulus` | `testbench_stimulus_bug` / `fix_testbench_or_stimulus` | `reachable_coverage_gap` / `add_directed_test_or_sequence` | The rerun treated a stimulus issue as a reachable coverage gap. |

The following pre-existing miss remained:

| Case | Gold issue/action | v1.1.2 prediction | v1.1.5 prediction | Note |
| --- | --- | --- | --- | --- |
| `fifo_D17` | `testbench_stimulus_bug` / `fix_testbench_or_stimulus` | `reachable_coverage_gap` / `add_directed_test_or_sequence` | `reachable_coverage_gap` / `add_directed_test_or_sequence` | The model continues to treat this stimulus problem as a directed coverage-generation opportunity. |

## Interpretation

The full rerun supports transfer of the scoped assumption/vacuity improvement to the full 53-case local Qwen triage setting. It is not only a replay or deterministic normalization result: all 53 outputs were produced by the local Qwen backend with `source=llm`, valid JSON rate 1.000, fallback rate 0.000, and LLM error rate 0.000.

The result still depends on the updated evidence and prompt path. It should be reported as real local Qwen performance under the v1.1.5 structured evidence/prompt/normalization pipeline, not as a model-only ablation. No `Aligned issue/action` normalization notes were observed in the after-rerun raw output, and the corrected assumption cases cite assumption/vacuity evidence in their ranked root-cause evidence. This suggests the measured improvement primarily came through the structured evidence/prompt path rather than visible post-hoc override, but the run is not an ablation separating those components.

The main side effect is a one-case regression in `testbench_stimulus_bug`: `rv_B8` changed from correct to `reachable_coverage_gap`. Together with the existing `fifo_D17` miss, this indicates that the next triage iteration should distinguish testbench stimulus gaps from reachable coverage goals more explicitly before broadening claims.

## Claims Boundary

- This is a real local Qwen/Qwen3-14B-AWQ full triage rerun through `JASPERLOOP_LLM_CMD`.
- This is not Codex CLI performance.
- This is not JasperGold-backed triage validation.
- This does not rerun SVA repair or coverage closure.
- This does not establish formal correctness or production signoff.
- This does not prove official FVEval performance.

## Recommended Next Task

Open a focused ablation or follow-up PR for testbench-stimulus versus reachable-coverage-gap separation. The two remaining misses, `fifo_D17` and `rv_B8`, should be analyzed before claiming the triage classifier is broadly solved.
