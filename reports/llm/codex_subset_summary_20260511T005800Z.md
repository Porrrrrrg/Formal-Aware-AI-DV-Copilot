# Codex Subset Evaluation Summary

Run UTC: 2026-05-11T00:58:00Z
Branch: `stage/codex-subset-eval`
Base HEAD before artifacts: `1445396df1cfe1da1325a5065bb659d054f92a98`
Manifest: `reports/llm/codex_subset_manifest_20260511T005800Z.json`

This report is a Stage 2B subset evaluation only. It is not a full benchmark, not a
production-readiness claim, and not a Codex versus Qwen/cloud comparison.

## Scope Notes

- Only the requested 3-case subsets were run: SVA repair, triage, and coverage.
- Qwen was not run.
- Full benchmarks were not run.
- The SVA repair outcomes are scaffold-level subset outcomes, not final
  JasperGold proof evidence. The run reports `jasper_syntax_pass_final`,
  `proven_final`, and `vacuous_final` as zero because no live JasperGold final
  proof was run in this subset.
- Triage and coverage LLM calls failed schema validation and used deterministic
  structured fallback outputs. Those fallback classifications are reported as
  fallback behavior, not Codex LLM evidence.
- Prompt inputs contained JasperGold-only evidence, separated from the
  deterministic scaffold and fallback outputs.

## Commands Run

| Step | Command | Result |
| --- | --- | --- |
| Preflight | `python -m pytest -q` | Passed, 65 tests |
| Preflight | `python -m ruff check .` | Passed |
| Prompt audit | `python scripts/export_codex_prompts.py --task all --limit 3 --summary-only` | Passed, 9 prompts |
| Healthcheck | `python scripts/run_codex_llm_eval.py --task healthcheck` | Passed, valid JSON |
| Subset | `python scripts/run_codex_llm_eval.py --task sva_repair --limit 3 --acknowledge-external-send` | 3 attempted |
| Subset | `python scripts/run_codex_llm_eval.py --task triage --limit 3 --acknowledge-external-send` | 3 attempted |
| Subset | `python scripts/run_codex_llm_eval.py --task coverage --limit 3 --acknowledge-external-send` | 3 attempted |

## Prompt Audit Summary

- Prompts exported: 9
- Prompt task mix: 3 SVA repair, 3 triage, 3 coverage
- Max prompt size: 3536 characters
- Total approximate tokens: 4710
- Prompts with gold labels: 0
- Prompts with RTL context: 0
- Prompts with JasperGold evidence: 9

## Aggregate Metrics

| Metric | Value |
| --- | ---: |
| Cases attempted | 9 |
| LLM valid JSON rate | 3/9 = 33.3% |
| Fallback rate | 6/9 = 66.7% |
| LLM error rate | 6/9 = 66.7% |
| Hallucinated signal rate, tasks where defined | 0/6 = 0.0% |

The final evaluator artifact JSON files were parseable. The valid JSON rate
above measures Codex LLM responses, not deterministic fallback artifacts.

## Task Results

| Task | Cases Attempted | Source Counts | Valid JSON Rate | Fallback Rate | LLM Error Rate | Hallucinated Signal Rate | Result |
| --- | ---: | --- | ---: | ---: | ---: | ---: | --- |
| SVA repair | 3 | `llm`: 3 | 100.0% | 0.0% | 0.0% | 0.0% | 3/3 scaffold pass after 1 repair round; exact match final 3/3 |
| Triage | 3 | `structured_fallback`: 3 | 0.0% | 100.0% | 100.0% | 0.0% | 3/3 fallback classifications matched expected labels |
| Coverage | 3 | `structured_fallback`: 3 | 0.0% | 100.0% | 100.0% | N/A | 3/3 fallback classifications matched expected labels |

## Cases Attempted

| Task | Case ID | Design | Source | Outcome |
| --- | --- | --- | --- | --- |
| SVA repair | `repair_arbiter_mutex_syntax` | `arbiter_rr2` | `llm` | Repaired missing semicolon; final scaffold pass |
| SVA repair | `repair_arbiter_spurious_unknown_signal` | `arbiter_rr2` | `llm` | Replaced hallucinated `grant0` with `gnt0`; final scaffold pass |
| SVA repair | `repair_arbiter_single_req1_wrong_grant` | `arbiter_rr2` | `llm` | Corrected grant polarity; final scaffold pass |
| Triage | `apb_C6` | `apb_regblock` | `structured_fallback` | LLM schema error; fallback predicted assertion property bug |
| Triage | `apb_C5` | `apb_regblock` | `structured_fallback` | LLM schema error; fallback predicted assertion property bug |
| Triage | `apb_C7` | `apb_regblock` | `structured_fallback` | LLM schema error; fallback predicted assumption constraint bug |
| Coverage | `apb_C10` | `apb_regblock` | `structured_fallback` | LLM schema error; fallback predicted unreachable or invalid coverage goal |
| Coverage | `apb_C9` | `apb_regblock` | `structured_fallback` | LLM schema error; fallback predicted reachable coverage gap |
| Coverage | `apb_C8` | `apb_regblock` | `structured_fallback` | LLM schema error; fallback predicted reachable coverage gap |

## Failure Examples

- Triage cases `apb_C6`, `apb_C5`, and `apb_C7` failed before model output
  because the Codex response schema was rejected: `root_cause_ranked.items`
  required `additionalProperties: false`. The evaluator then emitted
  deterministic `structured_fallback` outputs.
- Coverage cases `apb_C10`, `apb_C9`, and `apb_C8` failed before model output
  because the Codex response schema was rejected: top-level `required` was
  missing `case_id`. The evaluator then emitted deterministic
  `structured_fallback` outputs.
- SVA repair had intended round-0 scaffold failures in all 3 cases. All 3 were
  repaired by Codex LLM output in one round and ended in scaffold pass.

## Artifact Trace

Raw local subset artifacts:

| Path | SHA256 | Size |
| --- | --- | ---: |
| `evaluation/results/sva_repair_codex_subset.json` | `577C54A842E7BE01467D09916D7A44C3CC8D5A6965E15763DF2ED5EF7713B23A` | 7953 bytes |
| `evaluation/results/agent_eval_codex_subset.json` | `BB9F230D9B01BB8ADF77390502780341A5DEF71D970C645305F8A555DCA28007` | 23728 bytes |
| `evaluation/results/coverage_eval_codex_subset.json` | `52ED66BBF943DEF8BF979A07C0EF23C3032ACF5A343879A00630F2415820FD3E` | 23664 bytes |

The raw JSON artifacts are ignored generated outputs and were not selected for
commit because the triage and coverage files include verbose local CLI error
logs. This committed report and manifest contain the sanitized subset summary.
