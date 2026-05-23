# Codex Schema Strictness Fix Summary

UTC timestamp: 2026-05-11 01:20:33

Scope: Stage 2C response schema repair for the same 3+3+3 Codex subset only. This is not a full benchmark, not a Qwen/cloud comparison, and not a final research result.

## Schema Changes

| Schema | Change |
| --- | --- |
| `copilot/schemas/diagnosis_output.schema.json` | Added `suspect_rtl_signals` and `suspect_assertions_or_assumptions` to top-level `required`; added `additionalProperties: false` to `root_cause_ranked.items`. |
| `copilot/schemas/coverage_closure_output.schema.json` | Added declared property `case_id` to top-level `required`. |
| `copilot/schemas/sva_generation_output.schema.json` | Changed top-level `additionalProperties` from `true` to `false`. |
| `copilot/schemas/sva_repair_output.schema.json` | Added nested `rounds.items.additionalProperties: false`; added `feedback` to nested item `required`; changed `feedback` to nullable `["string", "null"]`. |
| `copilot/schemas/sva_repair_candidate.schema.json` | Inspected; already strict, no schema edit needed. |

No core IR, `app/models/core.py`, `app/core` protocols, adapters, protected core schema paths, or Jasper reports were changed.

## Tests Run

| Command | Result |
| --- | --- |
| `python -m pytest -q tests\test_response_schemas_strict.py` | Pass, 2 tests |
| `python scripts/export_codex_prompts.py --task all --limit 3 --summary-only` | Pass, 9 prompts |
| `python scripts/run_codex_llm_eval.py --task healthcheck` | Pass |
| `python scripts/run_codex_llm_eval.py --task sva_repair --limit 3 --acknowledge-external-send` | Pass |
| `python scripts/run_codex_llm_eval.py --task triage --limit 3 --acknowledge-external-send` | Pass |
| `python scripts/run_codex_llm_eval.py --task coverage --limit 3 --acknowledge-external-send` | Pass |
| `python -m pytest -q` | Pass, 67 tests |
| `python -m ruff check .` | Pass |

## Before vs After

Stage 2B observed blocker baseline: SVA repair returned 3/3 valid JSON with 0 fallback; triage and coverage failed structured-output schema admission and fell back for all 6 cases. Overall valid JSON was 3/9, fallback was 6/9.

| Metric | Before Stage 2C | After Stage 2C |
| --- | ---: | ---: |
| Valid JSON rate | 33.3% (3/9) | 100.0% (9/9 case-level subset outputs) |
| Fallback rate | 66.7% (6/9) | 0.0% (0/9) |
| LLM error rate | 66.7% (6/9) | 0.0% (0/9) |

## Task Rerun Table

| Task | Cases | Source counts | Valid JSON / fallback | LLM error rate | Task outcome |
| --- | ---: | --- | --- | ---: | --- |
| SVA repair | 3 | `llm: 5` repair attempts | Valid JSON; fallback 0.0% | 0.0% | Still schema-valid. Repair success 2/3 by scaffold check; the remaining failure is task/model behavior, not JSON/schema fallback. |
| Triage | 3 | `llm: 3` | 3/3 valid JSON; fallback 0.0% | 0.0% | Triage now returns valid JSON for all 3 cases. |
| Coverage | 3 | `llm: 3` | 3/3 valid JSON; fallback 0.0% | 0.0% | Coverage now returns valid JSON for all 3 cases. |

Triage and coverage no longer fail for the Stage 2B schema blockers. No model-output JSON failures were observed in this same 3+3+3 subset rerun.

## Notes

- The prompt export reported 9 prompts, no gold labels, no RTL context, and Jasper evidence present for all 9 prompts.
- The SVA repair evaluator reports `num_outputs: 5` because one of the 3 repair cases required multiple LLM repair attempts.
- These results are limited to the same Stage 2B 3+3+3 subset and must not be interpreted as Codex full benchmark performance or production readiness.
