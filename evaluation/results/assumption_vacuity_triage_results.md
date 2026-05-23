# Assumption/Vacuity Triage Improvement Results

This note records the post-v1.1.4 assumption/vacuity triage iteration. It is
not a full local Qwen benchmark, not Codex CLI performance, and not a
JasperGold-backed result.

## Motivation

The v1.1.2 local Qwen full triage run classified only 3 of 12 gold
`assumption_constraint_bug` cases correctly. The common failure mode was not
JSON validity or signal hallucination. In several missed cases, the model's
explanation cited active assumptions that removed required behavior, but the
final label/action still selected `assertion_property_bug` and
`fix_assertion_property`.

## Changes Under Test

- Evidence packets now include derived, non-gold assumption/vacuity triage cues
  for blocking assumptions, reset-stuck assumptions, missing environment
  constraints, and vacuous property results.
- The triage prompt now renders an `ASSUMPTION_VACUITY_TRIAGE_HINTS` block and
  states that assumption/constraint evidence must map to
  `assumption_constraint_bug` and `fix_assumption_constraint`.
- LLM output normalization now aligns issue/action with high-priority
  assumption/vacuity evidence while keeping the adjustment visible in the debug
  checklist.

## Local Regression

Run command:

```bash
python evaluation/run_agent_eval.py --systems structured --packet-source minimal --cases <12 assumption_constraint_bug case files> --out artifacts/assumption_vacuity_triage/agent_eval_assumption_vacuity_local.json
```

Result:

| Scope | Cases | Source | Issue accuracy | Action accuracy | Hallucinated signal rate |
| --- | ---: | --- | ---: | ---: | ---: |
| Assumption/constraint gold cases | 12 | structured fallback | 1.000 | 1.000 | 0.000 |

Full local structured-fallback regression was also run with rebuilt packets:

| Scope | Cases | Source | Issue accuracy | Action accuracy | Hallucinated signal rate |
| --- | ---: | --- | ---: | ---: | ---: |
| All local triage cases | 53 | structured fallback | 0.981 | 0.981 | 0.000 |

The full local regression still has one non-assumption classification miss, so
this branch should not be described as a universal triage fix.

As a non-model replay check, the saved v1.1.2 local Qwen triage predictions for
the 12 assumption/constraint cases were passed through the updated normalizer
with rebuilt evidence packets. This replay reached 12/12 issue/action agreement.
This is not a real Qwen rerun and should not be reported as new model
performance; it only verifies that the new evidence and normalization path
addresses the previously observed label/action inconsistency.

## Real Local Qwen Assumption/Vacuity Gate

After restarting the local WSL/vLLM endpoint, backend preflight passed with:

```powershell
$env:JASPERLOOP_LLM_CMD="python D:\AI-DV\qwen_json_backend.py"
$env:LOCAL_BASE_URL="http://127.0.0.1:8000/v1"
$env:SERVED_MODEL_NAME="Qwen/Qwen3-14B-AWQ"
python scripts/doctor_llm_backend.py --json
python scripts/test_llm_backend_contract.py
```

The assumption/vacuity-only real-model triage run then used the 12 gold
`assumption_constraint_bug` cases only:

```powershell
python evaluation/run_agent_eval.py --systems structured --llm --cases <12 assumption_constraint_bug case files> --out evaluation/results/agent_eval_qwen_assumption_vacuity.json
```

Result:

| Scope | Cases | Source | Valid JSON | Fallback rate | LLM error rate | Hallucinated signal rate | Issue accuracy | Action accuracy |
| --- | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Assumption/constraint gold cases | 12 | local Qwen/Qwen3-14B-AWQ via vLLM | 1.000 | 0.000 | 0.000 | 0.000 | 1.000 | 1.000 |

Compared with the v1.1.2 full local Qwen baseline of 3/12 correct
`assumption_constraint_bug` classifications, this assumption-focused gate
reached 12/12 on the same gold issue class. This remains a scoped subset result,
not a full benchmark rerun and not JasperGold-backed triage validation.

The Windows Codex app executable remains subprocess-blocked with
`permission_denied`; this result uses the generic `JASPERLOOP_LLM_CMD` route and
must not be reported as Codex CLI performance.
