# Design2SVA Error Taxonomy

This taxonomy is for Stage 14 error analysis of the local Design2SVA
evaluation path. It separates candidate-level failures from wrapper, harness,
and root-cause isolation failures so JSON validity, SVA syntax, formal proof,
vacuity, reachability, and embedding evidence are not conflated.

The examples below cite committed artifacts by filename. They intentionally do
not paste large result payloads.

## Scope

Design2SVA rows carry a `failure_category` produced by
`evaluation/run_design2sva_eval.py`. Some rows also carry a
`root_cause_candidate` or `root_cause_detail` when native-reference and wrapper
diagnostics are available. Treat those as different axes:

- `failure_category`: what happened to this generated or reference assertion
  under syntax, signal, reachability, proof, and vacuity checks.
- `root_cause_candidate`: why the failure is more likely happening, once native
  harness and reference-wrapper evidence are considered.
- `root_cause_detail`: a more specific audit string, useful for Stage 11-13
  wrapper and harness triage.

The current row-level taxonomy in the evaluator includes:
`syntax_error`, `unknown_signal`, `reset_clock_mismatch`,
`unsupported_helper_code`, `overstrong_assertion`,
`weak_vacuous_assertion`, `unreachable_antecedent`,
`unreachable_cover_goal`, `temporal_mismatch`, and
`proven_non_vacuous`.

The root-cause taxonomy includes labels such as `design2sva_embedding_bug` and
`native_harness_unreachable`. In this note, `wrapper_embedding_bug` refers to
that same wrapper/embedding class; the committed artifacts use the name
`design2sva_embedding_bug`.

## Why Clean JSON And Syntax Are Not Enough

Schema-valid JSON only says the model output can be parsed into the expected
candidate object. Syntax-clean SVA only says the assertion can pass local or
Jasper syntax checks. Neither proves that the assertion describes the intended
behavior, triggers on a reachable state, avoids vacuity, uses the correct
clock/reset contract, or is embedded into a harness equivalent to the native
benchmark harness.

The Stage 6 result makes this concrete. `design2sva_eval_codex_subset.json`
reported clean structured output for the three-case Codex subset:
`valid_json_rate=1.000`, `fallback_rate=0.000`,
`hallucinated_signal_rate=0.000`, and `syntax@k=1.000`. The Jasper-checked
artifact, `design2sva_eval_codex_jasper_subset.json`, still classified all 18
checked rows as `weak_vacuous_assertion` and reported no useful proven or
non-vacuous result. `design2sva_results.md` records the same split.

Stage 10-13 add another reason not to stop at syntax. The initial
reference-oracle artifacts showed unreachable reference behavior through the
Design2SVA wrapper even though the native benchmark oracle proved the same
reference properties. Stage 12/13 repaired the wrapper path and reran committed
candidate artifacts, after which `design2sva_eval_codex_fixed_wrapper_rerun.json`
and `design2sva_eval_antivacuity_codex_fixed_wrapper_rerun.json` reported
`proven_non_vacuous` rows. That change was wrapper evidence, not a reason to
treat earlier syntax-clean output as sufficient.

## Failure Classes

| Class | Axis | Definition | Evidence and examples | Primary next action |
| --- | --- | --- | --- | --- |
| `syntax_error` | Candidate failure | JSON cannot be validated into a candidate, local SVA scaffold syntax fails, or Jasper reports a syntax error. Invalid JSON is placed here because the candidate cannot be checked further, but valid JSON is not a pass condition. | No committed measured Design2SVA row is currently classified as `syntax_error`. Adjacent SVA repair evidence exists in `evaluation/results/sva_repair_codex_full.json` and `reports/repair/sva_repair_failure_analysis_20260511T030712Z.md`, including syntax fixtures such as `repair_buffer_reset_syntax` and `repair_apb_setup_syntax`. | Fix candidate formatting or schema first; do not interpret proof, vacuity, or reachability until syntax is clean. |
| `unknown_signal` | Candidate failure | Candidate references identifiers outside the task-visible or retrieved signal set. | Current Design2SVA Codex subset artifacts report `hallucinated_signal_rate=0.000`; no committed Design2SVA row is classified as `unknown_signal`. Adjacent SVA repair evidence appears in `evaluation/results/sva_repair_codex_full.json` for unknown-signal repair cases. | Restrict to `visible_signals` and retrieved RTL symbols before running proof. |
| `reset_clock_mismatch` | Candidate failure or root cause | Candidate uses the wrong clock event, omits or misuses the expected reset, or uses a `disable iff` polarity inconsistent with the task contract. | The taxonomy is present in Design2SVA result files such as `design2sva_eval_reference_oracle_rootcause_jasper.json`. A committed dry-run root-cause fixture exercises the label in `evaluation/fixtures/design2sva_rootcause_dry_run.json`; the measured Design2SVA result set does not currently show a positive row. | Compare emitted clock/reset against `clock_reset` metadata and native harness behavior before interpreting formal status. |
| `unsupported_helper_code` | Candidate failure | Candidate emits helper code when the task policy disallows helper code, or places helper logic in a way the wrapper cannot safely embed. | The Design2SVA fixture policy disallows helper code for the local smoke cases, and the taxonomy is emitted in result metadata. No committed measured Design2SVA row is currently classified as `unsupported_helper_code`. | Remove helper code or add an explicit supported-helper policy before proof. |
| `overstrong_assertion` | Candidate failure | The assertion is syntactically valid and reachable enough to be checked, but Jasper falsifies it. The property is too strong for the RTL, assumptions, or intended behavior. | The taxonomy is present in committed Design2SVA result metadata. No committed measured Design2SVA row is currently classified as `overstrong_assertion`. Adjacent repair analysis in `reports/repair/sva_repair_failure_analysis_20260511T030712Z.md` documents overbroad or semantic repair misses, but those are not measured Design2SVA falsifications. | Inspect counterexample, weaken or correct the consequent/guard/timing, and preserve the intended transaction scope. |
| `weak_vacuous_assertion` | Candidate failure | Formal feedback indicates the assertion is vacuous, unreachable, or otherwise formally unhelpful when no more specific cover-before-assert bucket is available. | `design2sva_eval_codex_jasper_subset.json` classifies 18 checked rows as `weak_vacuous_assertion` after the syntax-clean Codex subset is run through JasperGold. `docs/design2sva_jasper_subset_error_analysis.md` summarizes the same Stage 6 outcome. | Add or inspect antecedent covers, reset/post-reset covers, and vacuity checks; do not count the assertion as useful. |
| `unreachable_antecedent` | Candidate failure | A generated implication has an extracted antecedent, but the companion cover for that antecedent is unreachable or uncovered under the same wrapper, clock, reset, and assumptions. | `design2sva_eval_anti_vacuity_jasper_subset.json` reports `unreachable_antecedent=12`; `design2sva_eval_antivacuity_codex_new_jasper_subset.json` reports `unreachable_antecedent=20`; `design2sva_eval_reference_oracle_jasper.json` reports two reference rows in this class. | Repair the trigger first: remove impossible conjunctions, align reset, or use a reachable interface-level transaction. |
| `unreachable_cover_goal` | Candidate failure | The cover goal itself is unreachable or uncovered, or no valid antecedent cover can be generated for the intended reachability check. | `design2sva_eval_anti_vacuity_jasper_subset.json` reports `unreachable_cover_goal=6`; `design2sva_eval_antivacuity_codex_new_jasper_subset.json` reports `unreachable_cover_goal=10`; `design2sva_eval_reference_oracle_jasper.json` reports one reference row in this class. | Debug cover construction, invariant handling, reset/post-reset reachability, and wrapper/harness setup before changing assertion semantics. |
| `temporal_mismatch` | Candidate failure | Candidate is structurally valid but does not match available temporal/reference feedback, or formal status is unknown/undetermined. In non-formal runs this often means syntax-clean output still failed reference-style temporal comparison. | `design2sva_eval_codex_subset.json` records `temporal_mismatch=9` while formal checking is `not_run`; `design2sva_eval_antivacuity_codex_new_subset.json` records `temporal_mismatch=15` before the Jasper replay/check stage. | Use reference intent, traces, or counterexamples to correct `|->` versus `|=>`, `$past`, cycle delay, and protocol phase choices. |
| `wrapper_embedding_bug` | Root cause | Native benchmark reference proves, but the same reference assertion fails when embedded through the Design2SVA wrapper. The committed root-cause label is `design2sva_embedding_bug`. | `design2sva_eval_reference_oracle_rootcause_jasper.json` reports `design2sva_embedding_bug=3`. `docs/design2sva_harness_rootcause_stage11.md` explains the native-proves/wrapper-fails isolation, and `docs/design2sva_wrapper_parity_stage12.md` documents the wrapper parity repair. | Fix wrapper topology, file order, property module naming, bind/instantiation path, assumption reuse, clock/reset setup, and label handling before judging generation quality. |
| `native_harness_unreachable` | Root cause | The native benchmark harness cannot prove or reach its own reference objective, so downstream wrapper or candidate failures cannot be attributed to generation yet. | The classifier supports this label, but the committed measured native oracle `design2sva_native_reference_oracle_jasper.json` reports three native references proven and no native-harness-unreachable rows. | Stop downstream attribution and debug benchmark harness, assumptions, bound, reset release, or task validity. |
| `proven_non_vacuous` | Positive outcome | Candidate or reference assertion is proven and not flagged vacuous, with required antecedent reachability satisfied or no antecedent cover required for invariants. This is a success bucket, not a failure. | `design2sva_eval_codex_fixed_wrapper_rerun.json` reports `proven_non_vacuous=9`; `design2sva_eval_antivacuity_codex_fixed_wrapper_rerun.json` reports `proven_non_vacuous=15`; `design2sva_eval_reference_oracle_fixed_wrapper_sanity.json` reports `proven_non_vacuous=3`. | Record as useful formal evidence for the measured subset and preserve provenance, backend, wrapper, and replay details. |

## Classification Order

The evaluator intentionally checks structural problems before formal outcomes:

1. JSON/schema validity, unsupported helper code, hallucinated identifiers, and
   SVA syntax.
2. Backend-blocked status and clock/reset contract mismatches.
3. Formal proof outcomes: falsified, vacuous, unreachable, uncovered,
   unknown/undetermined, or proven.
4. Antecedent-cover metadata, which refines generic unreachable outcomes into
   `unreachable_antecedent` or `unreachable_cover_goal`.
5. Exact/reference comparison in non-formal modes, which can produce
   `temporal_mismatch`.

This order prevents a syntactically valid assertion with an unknown signal,
wrong reset polarity, or unreachable trigger from being counted as a useful
assertion simply because some later field is missing or optimistic.

## Root-Cause Ladder

Use native and reference-oracle artifacts in this order when interpreting a
failure:

1. Native reference oracle: if the native benchmark reference is unreachable or
   invalid, classify as `native_harness_unreachable` or reference-task invalid
   before looking at generated candidates.
2. Design2SVA reference embedding: if native proves but wrapper embedding
   fails, classify the issue as `wrapper_embedding_bug`/`design2sva_embedding_bug`.
3. Reset/post-reset diagnostics: if the wrapper cannot leave reset or observe a
   post-reset cycle, debug the wrapper/harness clock-reset setup.
4. Candidate antecedent cover: if native and wrapper baselines are healthy but
   the candidate trigger is unreachable, classify as candidate-generation or
   repair feedback.
5. Assertion proof and vacuity: only after reachability is established should a
   proof be interpreted as `proven_non_vacuous`, `overstrong_assertion`,
   `weak_vacuous_assertion`, or `temporal_mismatch`.

The key committed files for this ladder are:

- `design2sva_native_reference_oracle_jasper.json`
- `design2sva_eval_reference_oracle_jasper.json`
- `design2sva_eval_reference_oracle_rootcause_jasper.json`
- `design2sva_eval_reference_oracle_parity_jasper.json`
- `design2sva_eval_reference_oracle_fixed_wrapper_sanity.json`

## Reporting Rules

- Always report candidate provenance: deterministic scaffold, replay, committed
  Codex candidate replay, real LLM, reference oracle, or native oracle.
- Keep `valid_json_rate`, `syntax@*`, `proven@*`, and `proven_non_vacuous@*`
  separate. They answer different questions.
- Treat dry-run and replay results as plumbing or deterministic rerun evidence
  unless the artifact records measured JasperGold status.
- Cite filenames and aggregate counts rather than pasting raw JSON.
- Do not infer broad Design2SVA capability from a small local subset or from
  syntax/schema metrics alone.
