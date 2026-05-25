# Stimulus-vs-Coverage Triage Improvement Results

Date: 2026-05-25

Scope: focused post-v1.1.6 triage iteration for distinguishing `testbench_stimulus_bug` from `reachable_coverage_gap`.

This is not a full benchmark rerun, not SVA repair or coverage-closure rerun, not JasperGold-backed validation, not Codex CLI performance, and not an official FVEval result.

## Motivation

The v1.1.6 full local Qwen triage rerun fixed the assumption/vacuity weakness but left a stimulus-vs-coverage boundary issue:

| Case | v1.1.6 result | Gold label | Failure mode |
| --- | --- | --- | --- |
| `rv_B8` | `reachable_coverage_gap` / `add_directed_test_or_sequence` | `testbench_stimulus_bug` / `fix_testbench_or_stimulus` | Regressed from the v1.1.2 Qwen prediction; the model treated a missing dequeue stimulus as coverage closure. |
| `fifo_D17` | `reachable_coverage_gap` / `add_directed_test_or_sequence` | `testbench_stimulus_bug` / `fix_testbench_or_stimulus` | Persistent miss; the model treated missing `pop_ready` stimulus as a directed coverage-generation opportunity. |

The common ambiguity is that both classes can mention a reachable but unhit cover goal. The distinction is whether the task is diagnosing a broken or incomplete existing stimulus environment, or whether coverage closure should synthesize a new directed sequence for a valid reachable goal.

## Decision Rules

- If the issue is caused by missing or insufficient stimulus or environment driving, classify as `testbench_stimulus_bug` and recommend `fix_testbench_or_stimulus`.
- If formal cover/witness evidence or an explicit directed sequence shows the goal is reachable under a valid environment, classify as `reachable_coverage_gap` and recommend `add_directed_test_or_sequence`.
- If a coverage goal is illegal, invalid, or unreachable, classify as `unreachable_or_invalid_coverage_goal` and recommend `prove_unreachable_or_waive_coverage_goal`.
- An unhit coverage goal alone is insufficient evidence for `reachable_coverage_gap`; do not classify a stimulus/testbench problem as coverage closure merely because a cover goal has zero hits.

## Changes Under Test

- Evidence packets now include a derived, non-gold `stimulus_context` with stimulus-vs-coverage cues.
- The triage prompt now renders `STIMULUS_VS_COVERAGE_HINTS` and states the conservative decision rules above.
- Structured fallback uses `stimulus_context.triage_direction` before the older broad coverage-context heuristic.
- LLM normalization can align `reachable_coverage_gap` or `assertion_property_bug` to `testbench_stimulus_bug` only when strong stimulus-vs-coverage evidence supports that adjustment. Any such adjustment is recorded in `debug_checklist`.
- The stimulus cue extractor was kept narrow. It uses task type, coverage reachability, lack of witness/suggested sequence, liveness/fairness ready-valid context, and explicit simulation/testbench wording. It does not read benchmark labels.

## Structured Regression

Run command:

```powershell
python scripts/build_all_evidence_packets.py
python evaluation/run_agent_eval.py --systems structured --out artifacts/stimulus_vs_coverage/structured_after_fix.json
```

Result:

| Scope | Cases | Source | Issue accuracy | Action accuracy | Hallucinated signal rate |
| --- | ---: | --- | ---: | ---: | ---: |
| All local triage cases | 53 | structured fallback | 1.000 | 1.000 | 0.000 |

Target-label guardrails:

| Gold issue type | Cases | Issue/action |
| --- | ---: | ---: |
| `testbench_stimulus_bug` | 4 | 4/4 |
| `reachable_coverage_gap` | 9 | 9/9 |
| `unreachable_or_invalid_coverage_goal` | 5 | 5/5 |
| `assumption_constraint_bug` | 12 | 12/12 |

## Real Local Qwen Scoped Gate

Backend:

```powershell
$env:JASPERLOOP_LLM_CMD="python D:\AI-DV\qwen_json_backend.py"
$env:LOCAL_BASE_URL="http://127.0.0.1:8000/v1"
$env:SERVED_MODEL_NAME="Qwen/Qwen3-14B-AWQ"
python scripts/doctor_llm_backend.py --json
python scripts/test_llm_backend_contract.py
```

The scoped real-model gate covered:

- all 4 `testbench_stimulus_bug` cases
- all 9 `reachable_coverage_gap` cases
- all 5 `unreachable_or_invalid_coverage_goal` guardrail cases

Run command:

```powershell
python evaluation/run_agent_eval.py --systems structured --llm --cases <18 stimulus/coverage/invalid case files> --out evaluation/results/agent_eval_qwen_stimulus_vs_coverage.json
```

Result:

| Scope | Cases | Source | Valid JSON | Fallback | LLM error | Hallucinated signals | Issue accuracy | Action accuracy |
| --- | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Stimulus-vs-coverage scoped gate | 18 | local Qwen/Qwen3-14B-AWQ via vLLM | 1.000 | 0.000 | 0.000 | 0.000 | 1.000 | 1.000 |

Per-label result:

| Gold issue type | Cases | Issue/action |
| --- | ---: | ---: |
| `testbench_stimulus_bug` | 4 | 4/4 |
| `reachable_coverage_gap` | 9 | 9/9 |
| `unreachable_or_invalid_coverage_goal` | 5 | 5/5 |

Key cases:

| Case | Gold label | Scoped Qwen result | Evidence used |
| --- | --- | --- | --- |
| `rv_B8` | `testbench_stimulus_bug` / `fix_testbench_or_stimulus` | `testbench_stimulus_bug` / `fix_testbench_or_stimulus` | `stimulus_context` identified simulation/testbench stimulus absence and failure-triage unhit reachable cover without witness or directed sequence. |
| `fifo_D17` | `testbench_stimulus_bug` / `fix_testbench_or_stimulus` | `testbench_stimulus_bug` / `fix_testbench_or_stimulus` | `stimulus_context` identified failure-triage unhit reachable cover and liveness/fairness ready-valid stimulus dependence. |

The raw Qwen JSON output remains ignored at `evaluation/results/agent_eval_qwen_stimulus_vs_coverage.json`; this Markdown file is the versioned curated summary.

## Interpretation

The scoped gate supports the local mechanism change: structured stimulus-vs-coverage cues corrected the two known misses without regressing reachable coverage or invalid/unreachable coverage guardrails in the scoped real-model run.

This does not prove a full benchmark improvement yet. The next step should be a separate full local Qwen triage rerun to check whether the scoped improvement transfers to the full 53-case setting and whether non-target labels remain stable.

## Claims Boundary

- This is a targeted structured evidence and local Qwen scoped-gate result.
- This is not Codex CLI performance.
- This is not JasperGold-backed validation.
- This is not a full triage benchmark rerun.
- This does not rerun SVA repair or coverage closure.
- This does not claim official FVEval performance or production signoff.
