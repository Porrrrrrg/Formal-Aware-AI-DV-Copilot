# Local Qwen Full Triage Rerun After Stimulus-vs-Coverage Improvement

Date: 2026-05-25

Backend: `JASPERLOOP_LLM_CMD=python D:\AI-DV\qwen_json_backend.py`, calling a local vLLM OpenAI-compatible endpoint serving `Qwen/Qwen3-14B-AWQ` at `http://127.0.0.1:8000/v1`.

Result type: real local LLM full failure-triage rerun after the v1.1.7 stimulus-vs-coverage triage improvement. This is not Codex CLI performance, not an SVA repair or coverage-closure rerun, not JasperGold-backed validation, not deterministic scaffold performance, and not an official FVEval result.

Raw JSON was written locally to `evaluation/results/agent_eval_qwen_full_after_stimulus_coverage.json`. That file remains ignored; this Markdown file is the curated summary intended for version control.

## Gate Metrics

| Run | Cases | Valid JSON | LLM Success | Fallback | LLM Error | Hallucinated Signals | Issue Accuracy | Action Accuracy |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| v1.1.2 full local Qwen triage | 53 | 0.981 | 0.981 | 0.019 | 0.019 | 0.000 | 0.811 | 0.811 |
| v1.1.6 after assumption/vacuity rerun | 53 | 1.000 | 1.000 | 0.000 | 0.000 | 0.000 | 0.962 | 0.962 |
| v1.1.7 after stimulus-vs-coverage rerun | 53 | 1.000 | 1.000 | 0.000 | 0.000 | 0.000 | 1.000 | 1.000 |

Gate decision: the after-stimulus-vs-coverage full rerun passed the local output-mechanics gate. It produced 53/53 real LLM outputs, no deterministic fallback, no JSON failures, and no hallucinated suspect RTL signals.

## Per-Label Accuracy

| Gold issue type | Cases | v1.1.2 issue/action | v1.1.6 issue/action | v1.1.7 issue/action | Result |
| --- | ---: | ---: | ---: | ---: | --- |
| `assertion_property_bug` | 12 | 12/12 | 12/12 | 12/12 | no regression |
| `assumption_constraint_bug` | 12 | 3/12 | 12/12 | 12/12 | improvement retained |
| `reachable_coverage_gap` | 9 | 9/9 | 9/9 | 9/9 | no regression |
| `rtl_design_bug` | 11 | 11/11 | 11/11 | 11/11 | no regression |
| `testbench_stimulus_bug` | 4 | 3/4 | 2/4 | 4/4 | fixed remaining misses |
| `unreachable_or_invalid_coverage_goal` | 5 | 5/5 | 5/5 | 5/5 | no regression |

Overall issue/action accuracy improved from 43/53 in v1.1.2 to 51/53 in v1.1.6 and 53/53 in this full rerun.

## Target Case Outcomes

| Case | Gold issue/action | v1.1.6 prediction | v1.1.7 prediction | Result |
| --- | --- | --- | --- | --- |
| `rv_B8` | `testbench_stimulus_bug` / `fix_testbench_or_stimulus` | `reachable_coverage_gap` / `add_directed_test_or_sequence` | `testbench_stimulus_bug` / `fix_testbench_or_stimulus` | fixed |
| `fifo_D17` | `testbench_stimulus_bug` / `fix_testbench_or_stimulus` | `reachable_coverage_gap` / `add_directed_test_or_sequence` | `testbench_stimulus_bug` / `fix_testbench_or_stimulus` | fixed |

The stimulus-vs-coverage fix transferred from the scoped 18-case gate to the full 53-case setting. Both known misses now classify as `testbench_stimulus_bug` with `fix_testbench_or_stimulus`.

## Regression Analysis

The reachable and invalid coverage guardrails did not regress:

- `reachable_coverage_gap`: 9/9 issue/action in v1.1.6 and 9/9 in this rerun.
- `unreachable_or_invalid_coverage_goal`: 5/5 issue/action in v1.1.6 and 5/5 in this rerun.
- `assumption_constraint_bug`: stayed at 12/12 after the v1.1.5 assumption/vacuity improvement.

No new non-target regressions were observed. The predicted issue distribution matched the gold distribution exactly:

| Issue type | Predicted | Gold |
| --- | ---: | ---: |
| `assertion_property_bug` | 12 | 12 |
| `assumption_constraint_bug` | 12 | 12 |
| `reachable_coverage_gap` | 9 | 9 |
| `rtl_design_bug` | 11 | 11 |
| `testbench_stimulus_bug` | 4 | 4 |
| `unreachable_or_invalid_coverage_goal` | 5 | 5 |

## Interpretation

This rerun supports transfer of the scoped stimulus-vs-coverage improvement to the full local Qwen triage benchmark. The prior residual ambiguity between existing stimulus/testbench incompleteness and true reachable coverage closure was resolved for the two known cases without reducing reachable-coverage or invalid-coverage accuracy.

The result should still be reported as local Qwen performance under the current structured evidence, prompt, and normalization pipeline. It is not a model-only ablation, and it does not establish formal correctness. It only validates failure-triage output behavior for the current 53-case benchmark under the local Qwen backend.

## Claims Boundary

- This is a real local Qwen/Qwen3-14B-AWQ full failure-triage rerun through `JASPERLOOP_LLM_CMD`.
- This is not Codex CLI performance.
- This is not JasperGold-backed triage validation.
- This does not rerun SVA repair or coverage closure.
- This does not establish formal correctness or production signoff.
- This does not prove official FVEval performance.

## Recommended Next Task

Freeze this as the full-triage transfer checkpoint before starting another feature task. A useful follow-up would be an ablation that separates the contribution of `stimulus_context`, prompt wording, and normalization, or a JasperGold-backed expansion that turns coverage/stimulus evidence into stronger formal witness and unreachability signals.
