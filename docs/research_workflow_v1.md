# Research Workflow v1: v0.13 to Final Report

This workflow starts from the current v0.13 evidence boundary: Stage 13 fixed
Design2SVA wrapper reruns over committed Codex candidates and local
reference-oracle sanity artifacts. It ends with a final research report and
demo package. It is a research workflow only; it does not support production
signoff, unattended verification signoff, or coverage closure signoff.

External LLM benchmark sends are allowed only in Stage D after explicit operator
approval and prompt audit. This document was prepared without running external
LLM prompts.

Common result fields to preserve across stages:

- Provenance: command, git SHA, case list, prompt version, source counts, and
  whether any external prompt was sent.
- Model plumbing: `valid_json_rate`, `fallback_rate`, `real_llm_count`,
  `llm_error_rate`, and `source_counts`.
- Formal metrics: `formal_metrics_status`, `syntax@k`, `proven@k`,
  `proven_non_vacuous@k`, vacuity or reachability status, and
  `root_cause_detail_counts`.
- Quality gates: `hallucinated_signal_rate`, exact/reference match when
  applicable, and task-specific accuracy denominators.

## Stage A: Fixed-Wrapper Rerun Sanity

Objective: Reproduce the current v0.13 fixed-wrapper baseline before expanding
the study.

Input artifacts:

- `benchmarks/design2sva_cases.json`
- `evaluation/results/design2sva_eval_codex_subset.json`
- `evaluation/results/design2sva_eval_antivacuity_codex_new_subset.json`
- `evaluation/results/design2sva_native_reference_oracle_jasper.json`
- Stage 13 outputs under `evaluation/results/design2sva_eval_*fixed_wrapper*.json`

Commands:

```bash
python evaluation/run_design2sva_fixed_wrapper_rerun.py --only all
python evaluation/run_design2sva_fixed_wrapper_rerun.py --only all --dry-run
```

Metrics:

- `formal_metrics_status`
- `syntax@k`, `proven@k`, `proven_non_vacuous@k`
- `valid_json_rate`, `fallback_rate`, `source_counts`
- `llm_prompts_sent` or equivalent provenance field
- `root_cause_detail_counts`

Success criteria:

- Rerun artifacts are regenerated or confirmed with the same case counts:
  original Codex subset `3` cases at `k=3`, anti-vacuity subset `3` cases at
  `k=5`, and reference sanity `3` cases at `k=1`.
- On Moore/JasperGold, formal metrics are `measured`; on a local machine
  without JasperGold, blocked formal metrics are recorded as a tooling boundary.
- No new external LLM prompts are sent.

Failure interpretation:

- Candidate extraction or JSON failure is a provenance/artifact regression.
- `formal_metrics_status=blocked` on a machine without JasperGold is not model
  evidence.
- A measured drop after Stage 13 indicates wrapper, harness, or candidate replay
  regression and blocks expansion.

Allowed claims:

- The fixed-wrapper replay path is reproducible for the named artifacts.
- The measured three-case rerun can be described exactly as measured.
- Do not claim broad Design2SVA success or production readiness.

## Stage B: Local Fixture Expansion

Objective: Expand and stabilize the local Design2SVA fixture surface before any
new model send.

Input artifacts:

- `benchmarks/design2sva_cases.json`
- `copilot/schemas/design2sva_task.schema.json`
- `copilot/schemas/design2sva_candidate.schema.json`
- `evaluation/fixtures/design2sva_replay_outputs.jsonl`
- `evaluation/fixtures/design2sva_anti_vacuity_replay.jsonl`

Commands:

```bash
python evaluation/run_design2sva_eval.py --k 3 --dry-run --out evaluation/results/design2sva_eval_local_expanded.json --markdown evaluation/results/design2sva_eval_local_expanded.md
python evaluation/run_design2sva_eval.py --k 3 --replay evaluation/fixtures/design2sva_replay_outputs.jsonl --out evaluation/results/design2sva_eval_replay_expanded.json --markdown evaluation/results/design2sva_eval_replay_expanded.md
```

Metrics:

- Case count and fixture coverage by design and property type
- `valid_json_rate`, `fallback_rate`, `source_counts`
- `syntax@k`
- `hallucinated_signal_rate`
- Context-budget truncation or missing-field counts

Success criteria:

- Every local fixture has valid task schema, bounded context, visible-signal
  metadata, clock/reset metadata, and evaluation metadata.
- Dry-run and replay outputs are parseable and deterministic.
- No generated candidate references a signal outside the allowed signal set.

Failure interpretation:

- Schema or context failures are fixture-quality issues.
- Replay mismatch is an evaluator/provenance issue.
- Local scaffold success is not LLM quality evidence.

Allowed claims:

- The expanded local fixture set exercises the workflow plumbing.
- Replay and deterministic scaffold runs validate local infrastructure only.
- Do not claim JasperGold proof or hosted model performance from this stage.

## Stage C: Reference/Native Oracle Validation

Objective: Confirm that local reference assertions prove in native flows and
that the Design2SVA wrapper preserves that behavior.

Input artifacts:

- `benchmarks/design2sva_cases.json`
- Native benchmark formal files under `benchmarks/*/formal/`
- `evaluation/fixtures/design2sva_reference_oracle_replay.jsonl`
- `evaluation/results/design2sva_native_reference_oracle_jasper.json`

Commands:

```bash
python evaluation/run_design2sva_native_oracle.py --out evaluation/results/design2sva_native_reference_oracle_jasper.json
python evaluation/run_design2sva_eval.py --reference-oracle --jasper-check --native-oracle-results evaluation/results/design2sva_native_reference_oracle_jasper.json --out evaluation/results/design2sva_eval_reference_oracle_jasper_v1.json --markdown evaluation/results/design2sva_eval_reference_oracle_jasper_v1.md
python evaluation/run_design2sva_eval.py --reference-oracle --jasper-replay evaluation/fixtures/design2sva_reference_oracle_replay.jsonl --native-oracle-results evaluation/results/design2sva_native_reference_oracle_jasper.json --out evaluation/results/design2sva_eval_reference_oracle_replay_v1.json --markdown evaluation/results/design2sva_eval_reference_oracle_replay_v1.md
```

Metrics:

- Native `reference_proven@1` and wrapper `reference_proven@1`
- `reference_non_vacuous@1`
- `reference_antecedent_reachable@1`
- `wrapper_parity_pass_rate`
- `root_cause_detail_counts`

Success criteria:

- Native and wrapper reference-oracle behavior match for all validated local
  fixtures.
- Reference assertions prove non-vacuously where the task definition expects a
  proven assertion.
- Any invariant without an antecedent is judged by proof and vacuity status, not
  by a missing antecedent cover.

Failure interpretation:

- Native oracle failure points to invalid reference SVA, harness constraints, or
  task definition.
- Native pass with wrapper failure points to wrapper embedding or Tcl/report
  parsing.
- Unreachable covers point to harness reachability or assumption constraints
  before candidate generation.

Allowed claims:

- The reference/native oracle validation establishes the local harness and
  wrapper boundary for the checked fixtures.
- It does not establish generated-candidate quality.
- It does not establish semantic intent equivalence beyond the checked local
  reference assertions.

## Stage D: Real LLM Subset Expansion

Objective: Expand real LLM evidence under an explicit data-send boundary after
prompt audit.

Input artifacts:

- Prompt export summaries from `scripts/export_codex_prompts.py`
- `benchmarks/design2sva_cases.json`
- Current task result artifacts under `evaluation/results/`
- Environment-provided LLM command, for example `JASPERLOOP_LLM_CMD`

Commands:

```bash
python scripts/export_codex_prompts.py --task all --limit 10 --summary-only
python scripts/run_codex_llm_eval.py --task healthcheck
python scripts/run_codex_llm_eval.py --task sva_repair --limit 10 --out evaluation/results/sva_repair_codex_expanded_subset.json --acknowledge-external-send
python scripts/run_codex_llm_eval.py --task triage --limit 10 --out evaluation/results/agent_eval_codex_expanded_subset.json --acknowledge-external-send
python scripts/run_codex_llm_eval.py --task coverage --limit 10 --out evaluation/results/coverage_eval_codex_expanded_subset.json --acknowledge-external-send
python evaluation/run_design2sva_eval.py --llm --llm-command "$JASPERLOOP_LLM_CMD" --k 5 --out evaluation/results/design2sva_eval_codex_expanded_subset.json --markdown evaluation/results/design2sva_eval_codex_expanded_subset.md
```

Metrics:

- Prompt audit: `contains_gold_label`, task coverage, and evidence type
  included in prompt summaries
- `valid_json_rate`, `fallback_rate`, `real_llm_count`, `llm_error_rate`
- `source_counts`, with fallback rows separated from real LLM rows
- `hallucinated_signal_rate`
- Task-specific subset accuracy denominators

Success criteria:

- Prompt audit shows no gold-label leakage before any benchmark send.
- Every external benchmark command is explicitly approved and recorded.
- Real LLM rows are distinguishable from fallback/scaffold rows.
- JSON validity and hallucinated-signal checks pass or failures are reported
  with exact denominators.

Failure interpretation:

- Health-check failure is adapter/connectivity/schema readiness failure.
- Invalid JSON or high LLM error rate blocks accuracy interpretation.
- Fallback rows preserve pipeline execution but are not model-quality evidence.
- Hallucinated signals point to prompt/context constraints or model behavior.

Allowed claims:

- The approved subset produced `N` real LLM rows and `M` fallback rows with the
  exact source counts.
- Accuracy may be reported only with denominators tied to real LLM rows or with
  fallback mix disclosed next to the number.
- Do not claim a subset is a full benchmark.

## Stage E: JasperGold-Measured Full Local Benchmark

Objective: Run JasperGold measurement over the full local Design2SVA benchmark
and the expanded replayable candidate set.

Input artifacts:

- Stage B expanded local fixture results
- Stage C native/reference oracle results
- Stage D real LLM Design2SVA subset, if approved and available
- `benchmarks/design2sva_cases.json`

Commands:

```bash
python evaluation/run_design2sva_eval.py --k 5 --jasper-check --native-oracle-results evaluation/results/design2sva_native_reference_oracle_jasper.json --out evaluation/results/design2sva_eval_local_jasper_full.json --markdown evaluation/results/design2sva_eval_local_jasper_full.md
python evaluation/run_design2sva_eval.py --replay evaluation/results/design2sva_eval_codex_expanded_subset.json --k 5 --jasper-check --native-oracle-results evaluation/results/design2sva_native_reference_oracle_jasper.json --out evaluation/results/design2sva_eval_codex_expanded_jasper.json --markdown evaluation/results/design2sva_eval_codex_expanded_jasper.md
```

Metrics:

- `formal_metrics_status`
- `syntax@k`, `proven@k`, `proven_non_vacuous@k`
- Reference oracle parity and reachability fields
- `root_cause_detail_counts`
- Per-case Jasper status: syntax error, proven, falsified, unreachable,
  bounded uncovered, blocked, or unknown

Success criteria:

- JasperGold runs are `measured`, not replayed or blocked, for all intended
  local cases.
- Candidate proof metrics are interpreted only after reference/native oracle
  parity is known.
- Per-case failures include enough wrapper audit and formal status data for
  error analysis.

Failure interpretation:

- `blocked` means tool/license/environment failure and is not candidate
  evidence.
- Syntax failure is a candidate or wrapper emission issue.
- Unreachable reference-oracle evidence points to harness constraints before
  model quality.
- Candidate failure with reference-oracle pass points to generation or repair
  selection.

Allowed claims:

- The run measures formal behavior of named candidates on named local fixtures
  under the checked harnesses and assumptions.
- A JasperGold proof pass is scoped to the exact harness, assumptions, property,
  and tool run.
- Do not claim semantic intent alignment or production signoff.

## Stage F: Ablation

Objective: Isolate which prompt, context, repair-loop, and evidence components
drive observed outcomes.

Input artifacts:

- Stage D real LLM subset outputs, if approved and available
- Stage E JasperGold-measured outputs
- Evaluation packets under the configured packet root
- Existing ablation registry under `docs/research/`

Commands:

```bash
python evaluation/run_agent_eval.py --all-systems --ablations no_assertion_manifest no_assumption_manifest no_jasper_cex no_coverage_context minimal_packet --out reports/research/runs/stage14_triage_ablation.json
python evaluation/run_sva_repair_ablation.py --case-set all --variants baseline_prompt cex_aware_prompt multi_round_repair one_round_repair self_check_before_final signal_whitelist_only temporal_hint_only --jasper-check --out reports/research/runs/stage14_sva_repair_ablation.json --summary-out reports/research/runs/stage14_sva_repair_ablation.md --manifest-out reports/research/runs/stage14_sva_repair_ablation_manifest.json
```

Metrics:

- Delta from baseline for issue-type accuracy, next-action accuracy, and repair
  success
- `valid_json_rate`, `fallback_rate`, `source_counts`, and LLM error rate
- JasperGold proof/vacuity metrics when `--jasper-check` is measured
- Per-variant failure categories

Success criteria:

- Ablations use matched case sets, prompt versions, and run conditions.
- Every delta is reported against a named baseline and exact denominator.
- LLM-backed ablations are separated from deterministic/local ablations.

Failure interpretation:

- Large drop after removing evidence identifies dependence on that evidence
  component.
- Noisy or unmatched runs do not support causal claims.
- Jasper-blocked ablations can still show local schema behavior but not formal
  proof deltas.

Allowed claims:

- A controlled ablation changed metric `X` by `Y` on matched cases.
- The evidence component is associated with the measured delta under those run
  conditions.
- Do not claim general causality outside the matched ablation setup.

## Stage G: Error Analysis

Objective: Convert misses and regressions into evidence-backed error categories
for the final report.

Input artifacts:

- Stage D subset outputs
- Stage E JasperGold-measured outputs
- Stage F ablation outputs
- Existing analyses such as `docs/full_codex_error_analysis.md` and
  `docs/design2sva_jasper_subset_error_analysis.md`

Commands:

```bash
python scripts/refresh_eval_results.py --packet-source actual
rg -n "\"source\"|\"root_cause_detail\"|\"hallucinated\"|\"formal_metrics_status\"|\"llm_error\"" evaluation/results reports/research
```

Metrics:

- Error counts by task, source, and case family
- Miss category counts: syntax, hallucinated signal, wrapper/harness,
  unreachable antecedent, weak/vacuous assertion, label-boundary miss, and
  unsupported recommendation
- Denominators for real LLM rows, fallback rows, and Jasper-measured rows

Success criteria:

- Every reported miss has a case ID, command/source artifact, observed output,
  expected label or reference, and assigned error category.
- Fallback, replay, and real LLM rows are never merged without disclosure.
- JasperGold failures are separated from scaffold/exact-match misses.

Failure interpretation:

- Missing provenance blocks publication of that row as evidence.
- Unclassifiable misses become residual risk, not success.
- Disagreement between stale markdown and raw JSON is resolved in favor of the
  current raw JSON artifact.

Allowed claims:

- The final report may state observed failure modes and counts for named
  artifacts.
- It may identify the largest measured error clusters.
- It may not convert error analysis into a signoff or deployment claim.

## Stage H: Final Report and Demo

Objective: Publish a coherent research report, result tables, and demo script
that preserve all claim boundaries.

Input artifacts:

- Stage A through G result JSON, markdown, manifests, and command records
- `reports/final/jasperloop_dv_final_report.md`
- `reports/final/jasperloop_dv_result_tables.md`
- `docs/demo_script.md`
- `docs/final_report.md`

Commands:

```bash
python scripts/refresh_eval_results.py --packet-source actual
python -m pytest
```

Metrics:

- Report table consistency with raw JSON artifacts
- Test pass/fail status
- Count of measured, replayed, dry-run, fallback, and real LLM rows
- Explicit unsupported-claim checklist coverage

Success criteria:

- Final tables cite exact artifacts, commands, case counts, and source counts.
- The report separates local scaffold, replay, real LLM, and JasperGold-measured
  evidence.
- Demo script states when outputs are committed fixtures, local dry runs,
  imported Moore/JasperGold evidence, or approved external LLM results.
- Unsupported claims are listed near the corresponding positive claims.

Failure interpretation:

- Test failures or table/artifact inconsistencies block final publication.
- Missing command provenance downgrades a result to anecdotal context.
- Any wording that implies production signoff must be removed.

Allowed claims:

- The project demonstrates a research prototype workflow with named local,
  LLM-backed, replay, and JasperGold-measured artifacts.
- The final report may state measured results only within their artifact,
  harness, prompt, and case-set boundaries.
- The demo may show workflow mechanics and evidence boundaries, not production
  readiness.
