# Local Qwen Full Benchmark Results

Date: 2026-05-23

Backend: `JASPERLOOP_LLM_CMD=python D:\AI-DV\qwen_json_backend.py`, calling a local vLLM OpenAI-compatible endpoint serving `Qwen/Qwen3-14B-AWQ` at `http://127.0.0.1:8000/v1`.

Result type: real local LLM full benchmark. This is not Codex CLI performance, not deterministic scaffold performance, not JasperGold-backed performance, and not an official FVEval result.

Raw JSON outputs were written locally for inspection. This Markdown file is the curated summary intended for version control.

## Gate Metrics

| Task | Cases | Outputs | Valid JSON | LLM Success | Fallback | LLM Error | Hallucinated Signals | Task Metric |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| SVA repair | 23 | 29 | 1.000 | 1.000 | 0.000 | 0.000 | 0.043 | final exact match / repair success 0.913 |
| Failure triage | 53 | 53 | 0.981 | 0.981 | 0.019 | 0.019 | 0.000 | issue/action accuracy 0.811 / 0.811 |
| Coverage closure | 14 | 14 | 1.000 | 1.000 | 0.000 | 0.000 | n/a | gap/action accuracy 1.000 / 1.000 |

Gate decision: passed the full-run output mechanics gate. Each measured task met JSON validity >= 0.90, fallback rate <= 0.25, and hallucinated signal rate <= 0.10 where the metric applies.

This gate result does not imply formal correctness or production readiness. The next research step is JasperGold-backed syntax/proof/vacuity re-check of the generated artifacts in an available formal environment.

## Task Findings

### SVA Repair

SVA repair produced valid JSON for all 29 LLM outputs and did not use deterministic fallback. The scaffold repair success / final exact match rate was 21/23.

Failures:

| Case | Design | Property | Bug type | Outcome |
| --- | --- | --- | --- | --- |
| `repair_arbiter_single_req1_wrong_grant` | `arbiter_rr2` | `p_single_req1_grant` | temporal or semantic error | Scaffold failed after 3 rounds; no hallucinated signal was reported. |
| `repair_fifo_reset_wrong_polarity` | `fifo_1r1w` | `p_reset_empty` | reset error | Scaffold failed after 3 rounds; `out_valid` was reported as a hallucinated signal. |

The `jasper_syntax_pass_final`, `proven_final`, and `vacuous_final` fields are not JasperGold-backed metrics in this run because JasperGold was not invoked.

### Failure Triage

Failure triage produced 52 real LLM outputs and 1 visible structured fallback from 53 attempted cases. The fallback case was `arbiter_A9`, where the backend returned malformed/truncated JSON after a repeated-field object; the evaluator counted it as fallback rather than model success.

The dominant task error is assumption/vacuity triage. Gold `assumption_constraint_bug` cases were often classified as `assertion_property_bug`, with the corresponding action changed from `fix_assumption_constraint` to `fix_assertion_property`.

Assumption/constraint examples:

| Case | Gold | Predicted | Gold action | Predicted action |
| --- | --- | --- | --- | --- |
| `apb_C11` | `assumption_constraint_bug` | `assertion_property_bug` | `fix_assumption_constraint` | `fix_assertion_property` |
| `apb_C7` | `assumption_constraint_bug` | `assertion_property_bug` | `fix_assumption_constraint` | `fix_assertion_property` |
| `arbiter_A11` | `assumption_constraint_bug` | `assertion_property_bug` | `fix_assumption_constraint` | `fix_assertion_property` |
| `fifo_D10` | `assumption_constraint_bug` | `assertion_property_bug` | `fix_assumption_constraint` | `fix_assertion_property` |
| `rv_B6` | `assumption_constraint_bug` | `assertion_property_bug` | `fix_assumption_constraint` | `fix_assertion_property` |

Gold assumption/constraint cases: 12. Correctly classified as assumption/constraint: 3. This is the main model-quality weakness surfaced by the full run.

Other triage example:

| Case | Gold | Predicted | Note |
| --- | --- | --- | --- |
| `fifo_D17` | `testbench_stimulus_bug` | `reachable_coverage_gap` | The model treated a stimulus issue as a directed coverage-generation opportunity. |

### Coverage Closure

Coverage closure completed 14/14 cases with valid JSON and no fallback. It correctly separated 9 reachable coverage gaps from 5 unreachable or invalid coverage goals. The wrong-test-suggestion rate was 0.000, and reachable-sequence presence was 1.000 for reachable cases.

Coverage closure does not currently report a hallucinated-signal rate for this run.

## Claims Boundary

- This is a real local Qwen backend result through `JASPERLOOP_LLM_CMD`.
- This is not Codex CLI performance.
- This is not JasperGold-backed validation.
- This does not establish full intent equivalence.
- This does not claim official FVEval performance.
- This does not justify running a larger model before analyzing the assumption/vacuity weakness.

## Recommended Next Task

Open a separate JasperGold-backed re-check PR if `JASPER_BIN`, `JASPER_ENV`, or `jg` is available. That PR should report syntax pass, proven/falsified/undetermined/vacuous counts, and cases where the local Qwen output is syntactically valid but semantically weak.
