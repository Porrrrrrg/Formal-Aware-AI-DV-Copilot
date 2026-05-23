# Real LLM Evaluation Protocol

This protocol is the claim boundary for JasperLoop-DV runs that use Codex or
another hosted LLM through `JASPERLOOP_LLM_CMD`. It separates prompt/export
readiness, synthetic health checks, deterministic scaffold results, and real
LLM-backed benchmark subsets.

## External Data Boundary

The prompt export command is local-only and sends nothing externally:

```bash
python scripts/export_codex_prompts.py --task all --limit 3 --summary-only
```

The Codex health check sends only a synthetic prompt asking for one SVA repair
JSON object. It does not send benchmark RTL, Jasper reports, evidence packets,
counterexamples, manifests, or labels:

```bash
python scripts/run_codex_llm_eval.py --task healthcheck
```

Benchmark tasks send local benchmark content to Codex/OpenAI when, and only
when, the operator explicitly runs with `--acknowledge-external-send`. Depending
on task, this can include:

- SVA repair: broken assertions, allowed signal names, property intent, and
  Jasper/scaffold feedback.
- Triage: evidence packets, JasperGold summaries, counterexample summaries,
  RTL excerpts, manifests, assumptions, and allowed issue/action sets.
- Coverage: coverage goals, reachability context, related signals, assumptions,
  Jasper coverage evidence, and directed-sequence context.

Gold labels are not supposed to be included in prompts. Use the prompt export
summary before any external benchmark run to check `contains_gold_label`.

## Three-Case Subsets

Run this local prompt audit before approving any benchmark send:

```bash
python scripts/export_codex_prompts.py --task all --limit 3 --summary-only
```

Run the synthetic connectivity/schema check:

```bash
python scripts/run_codex_llm_eval.py --task healthcheck
```

Only after explicit approval to export benchmark content, run one or more
three-case subsets:

```bash
python scripts/run_codex_llm_eval.py --task sva_repair --limit 3 --out evaluation/results/sva_repair_codex_subset.json --acknowledge-external-send
python scripts/run_codex_llm_eval.py --task triage --limit 3 --out evaluation/results/agent_eval_codex_subset.json --acknowledge-external-send
python scripts/run_codex_llm_eval.py --task coverage --limit 3 --out evaluation/results/coverage_eval_codex_subset.json --acknowledge-external-send
```

Do not add `--acknowledge-external-send` to exploratory, CI, documentation, or
prompt-audit commands. It is for deliberate externally sent benchmark subsets
only.

## Result Interpretation

The Codex wrapper prints a `codex_healthcheck_summary` for health checks and a
`codex_eval_readiness_summary` after successful benchmark subset runs. Read
these fields before discussing accuracy:

- `valid_json_rate`: fraction of attempted LLM calls that returned parseable
  JSON accepted by the local adapter path. A low value means the model run did
  not reliably produce usable structured output.
- `fallback_rate`: fraction of rows produced by deterministic fallback/scaffold
  logic rather than a successful real LLM output.
- `hallucinated_signal_rate`: fraction of checked rows that referenced signals
  outside the allowed signal set. For coverage, this is currently reported as
  `null` with `hallucinated_signal_checked_count: 0` because coverage outputs do
  not yet have a signal-hallucination checker.
- `source_counts`: raw counts of `llm`, `structured_fallback`,
  `raw_log_fallback`, `heuristic`, or other sources.
- `deterministic_scaffold_count` and `real_llm_count`: the explicit split
  between local scaffold/fallback rows and rows backed by a successful real LLM
  JSON response.
- `llm_error_count` and `llm_error_rate`: adapter, timeout, schema, JSON, or
  command failures that caused fallback.

Accuracy metrics are interpretable as Codex-backed only for rows counted under
`source_counts.llm` or `real_llm_count`. If fallback rows are present, report
them separately.

## Allowed Claims

Allowed:

- "The prompt export summary shows the first three prompts per task and whether
  they include gold labels, RTL context, and Jasper evidence."
- "The Codex health check returned valid JSON for one synthetic prompt" when
  `valid_json_rate` is `1.0` in `codex_healthcheck_summary`.
- "On the approved three-case subset, N rows were real LLM outputs and M rows
  fell back to deterministic scaffold logic" with the exact `source_counts`.
- "The measured subset accuracy for real LLM rows was X/Y" when computed only
  from rows whose source is `llm`.
- "Fallback rows preserved pipeline execution but are not Codex quality
  evidence."

Not allowed:

- Do not claim deterministic scaffold/fallback accuracy is Codex accuracy.
- Do not combine fallback rows and `llm` rows into a single "Codex accuracy"
  number unless the source mix is disclosed next to the number.
- Do not claim prompt-export readiness, health-check success, or schema
  validity proves benchmark performance.
- Do not claim a three-case subset is a full Codex benchmark.
- Do not claim Qwen-vs-Codex comparison without matched manifests and run
  conditions.
- Do not claim Jasper proof pass proves semantic intent alignment.
- Do not claim this workflow is production signoff automation.

## Claim Checklist

Before publishing or committing any real LLM evaluation statement, verify:

- [ ] The exact command and result file are named.
- [ ] The command did not use `--acknowledge-external-send` unless benchmark
      export was explicitly approved.
- [ ] `valid_json_rate`, `fallback_rate`, `hallucinated_signal_rate`, and
      `source_counts` are reported or marked not applicable.
- [ ] `deterministic_scaffold_count` and `real_llm_count` are reported
      separately.
- [ ] Any accuracy numerator/denominator excludes fallback rows unless the
      fallback mix is explicitly disclosed.
- [ ] Prompt export summaries show no leaked gold labels before benchmark send.
- [ ] Health-check results are described only as connectivity/schema readiness.
- [ ] Three-case subsets are described as subsets, not full benchmarks.
- [ ] Deterministic scaffold accuracy is never described as Codex accuracy.
- [ ] Jasper proof, vacuity, and intent-alignment limitations remain stated.
