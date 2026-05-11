# JasperLoop-DV Final Report

This Stage 6A report consolidates existing JasperLoop-DV evidence. It uses
committed reports and documentation only. No new experiments, model calls,
JasperGold/Moore runs, benchmark label edits, prompt edits, schema edits, or
system-code changes were performed for this report.

Companion tables are in
`reports/final/jasperloop_dv_result_tables.md`.

## 1. Abstract

JasperLoop-DV is a formal-aware AI design-verification copilot prototype. Its
core principle is that the LLM is not the verification oracle: JasperGold is the
source of truth for syntax, proof, counterexamples, cover reachability, and
vacuity where those modes are actually run. The agent layer consumes structured
evidence packets and proposes assertion generation, assertion repair, failure
triage, and coverage-closure actions for engineer review.

The strongest recorded results are bounded to the committed reports. The local
DV benchmark has 53 expanded cases with 53/53 schema-valid prove-backed
Jasper/Moore evidence packets. The real Codex full benchmark attempted 57 cases
with 71/71 valid JSON outputs, 0 fallback, and 0 LLM errors, with task metrics
of 11/18 SVA repair scaffold success, 28/30 triage issue/action accuracy, and
9/9 coverage gap/action accuracy. Restored Codex repair candidates were later
validated on Moore/JasperGold with 34/34 syntax pass and 34/34 proven. A repair
ablation handoff artifact produced 126/126 syntax pass and 126/126 proven
candidates across seven variants. These proof results do not by themselves
prove intent alignment, and `not_flagged_vacuous` is not an explicit
non-vacuity certificate.

## 2. Motivation

LLM assistance is attractive in DV because engineers spend substantial time
writing assertions, diagnosing counterexamples, debugging assumptions, and
closing coverage holes. The risk is that fluent text or plausible SVA can hide
wrong intent, weak properties, hallucinated signals, or overconstrained proofs.
JasperLoop-DV addresses this by making formal evidence the central interface:
the model can summarize, repair, rank, and propose, but correctness claims are
bounded by checked artifacts and human review.

The project therefore targets practical DV ownership questions: whether the
likely fix belongs in RTL, an assertion, an assumption, testbench stimulus, or
a coverage plan. This motivation is stated in `docs/design_doc.md`,
`docs/literature_review.md`, and `docs/related_work_fveval_proofloop.md`.

## 3. Related Work Positioning

The local literature notes position JasperLoop-DV near FVEval and ProofLoop.
FVEval motivates evaluating generated SystemVerilog Assertions with formal
tools instead of text similarity alone. JasperLoop-DV adopts that principle for
SVA generation and repair, using JasperGold-backed syntax/proof/vacuity fields
when those checks are available. ProofLoop motivates a feedback loop in which
formal results constrain the next LLM attempt. JasperLoop-DV adopts that loop
for repair and extends the evidence-centered pattern to triage and coverage
closure.

The differentiation is workflow scope. JasperLoop-DV is not AI RTL generation
and not only assertion generation. It is a formal-aware DV assistant that
packages evidence for assertion repair, counterexample interpretation,
assumption debugging, coverage closure, and review prioritization. Sources:
`docs/literature_review.md` and `docs/related_work_fveval_proofloop.md`.

## 4. System Architecture

The system architecture is documented as a pipeline:

```text
RTL + Spec + SVA + Assumptions
        |
        v
JasperGold Formal Runner
        |
        v
Formal Evidence Extractor
        |
        v
Structured Evidence Packet
        |
        +--> SVA Generation Agent
        +--> SVA Repair Agent
        +--> DV Failure Triage Agent
        +--> Coverage Closure Agent
        |
        v
JasperGold Re-check / Evaluation
```

The Stage 5 CLI and workflow layers add user-facing commands, dry-run
manifests, Moore handoff preparation, local/replay/Codex backend routing, static
intent alignment, and local Qwen endpoint plumbing. The workflow defaults to
local dry-run behavior and records claim boundaries in manifests and reports.
Sources: `docs/design_doc.md`, `docs/cli_usage.md`,
`docs/workflow_usage.md`, and `reports/release/stage5_result_ledger_20260511T205601Z.md`.

## 5. Evidence Packet Design

The evidence packet is the central interface between formal tooling and model
reasoning. It records design identity, task type, property or coverage goal,
assertion and assumption intent, JasperGold proof/cover/counterexample/vacuity
results where present, RTL excerpts, signal-role maps, allowed issue labels,
and allowed next actions.

Counterexample summaries are role-aware. Raw VCD-derived signal events are
preserved in local artifacts, while the packet presents semantic events using
roles such as client request/grant, APB write data, or ready/valid handshake
signals. This design lets the model reason over compact DV evidence without
turning the model into the oracle. The primary packet evidence is recorded in
`reports/jasper/moore_evidence_summary_20260511T004654Z.md`; the expanded
packet evidence is recorded in
`reports/jasper/expanded_benchmark_evidence_summary_20260511T064639Z.md`.

## 6. Agent / Workflow Modes

JasperLoop-DV implements four agent modes:

| Mode | Input | Output | Source report(s) |
| --- | --- | --- | --- |
| SVA generation | RTL context plus natural-language property intent | Candidate SVA JSON with property id, generated SVA, referenced signals, and explanation | `docs/design_doc.md`; `reports/jasper/moore_evidence_summary_20260511T004654Z.md` |
| SVA repair | Failed SVA plus JasperGold/scaffold feedback | Repaired SVA, rationale, referenced signals, and expected status | `docs/design_doc.md`; `reports/llm/codex_full_summary_20260511T015713Z.md`; `reports/jasper/codex_repair_final_proof_summary_20260511T053413Z.md` |
| Failure triage | Failing assertion, counterexample, assumptions, and RTL context | Diagnosis JSON over RTL bug, assertion bug, assumption bug, stimulus bug, reachable coverage gap, or invalid/unreachable coverage goal | `docs/design_doc.md`; `reports/llm/codex_full_summary_20260511T015713Z.md` |
| Coverage closure | Coverage goal, observed hit count, formal reachability evidence, assumptions, and related signals | Coverage-gap classification, recommended closure action, and directed sequence or waiver/proof recommendation | `docs/design_doc.md`; `reports/llm/codex_full_summary_20260511T015713Z.md` |

Stage 5 added workflow modes for dry-run repair, triage, coverage, replay demo,
Moore handoff, static intent alignment, and local Qwen backend routing. These
are integration capabilities, not additional benchmark results. Sources:
`docs/workflow_usage.md`, `reports/workflows/workflow_smoke_summary_20260511T182158Z.md`,
and `reports/workflows/e2e_demo_summary_20260511T191259Z.md`.

## 7. Evaluation Setup

The evaluation evidence spans several bounded layers. The primary local-DV
benchmark initially covered three designs with 30 labeled cases. Stage 3
expanded local-DV metadata to 53 cases by adding the `fifo_1r1w` family and
additional assumption/vacuity cases. Stage 4 then upgraded the expanded set to
53/53 schema-valid prove-backed evidence packets. Codex was evaluated on 57
cases: 18 SVA repair, 30 triage, and 9 coverage. Separate Moore/JasperGold
proof checks validated restored repair candidates and ablation handoff
candidates.

External anchors were kept separate. The FVEval-compatible subset imported 30
cases and ran a local deterministic scaffold without JasperGold, Codex, or
Qwen. The local Qwen 3+3+3 subset ran only 9 workflow cases against a local
Qwen endpoint and was recorded as readiness evidence, not full benchmark
evidence.

The consolidated counts and source filenames are in
`reports/final/jasperloop_dv_result_tables.md`, Tables 1 and 2.

## 8. Stage-by-Stage Results

Stage 2 established the first evidence path: Moore/JasperGold evidence packets,
Codex subset/full infrastructure, schema strictness fixes, and Qwen readiness
checks. Stage 3 froze a baseline that included Moore packet evidence, the Codex
full benchmark, repair-output restoration, final proof handoff, benchmark
expansion metadata, and FVEval-compatible import. Stage 4 added prove-backed
expanded benchmark evidence, local FVEval-compatible evaluation, SVA repair
ablation results, and ablation final proof. Stage 5 added workflow packaging:
CLI, Moore handoff, intent alignment, replay demo, local Qwen backend, and repo
hygiene. Stage 5.5 imported sanitized DV skills and integrated playbook
guidance while preserving claim boundaries.

The stage summary is tabulated in
`reports/final/jasperloop_dv_result_tables.md`, Table 1. Primary source ledgers
are `reports/release/stage3_result_ledger_20260511T062042Z.md`,
`reports/release/stage4_result_ledger_20260511T152017Z.md`,
`reports/release/stage5_result_ledger_20260511T205601Z.md`, and
`reports/release/stage55_result_ledger_20260511T224417Z.md`.

## 9. Codex Benchmark Results

The real Codex full benchmark was run on 2026-05-11 and recorded 57 attempted
cases with 71 LLM adapter outputs. Aggregate validity was 71/71 valid JSON,
fallback was 0/71, LLM error rate was 0/71, hallucinated-signal rate for
defined tasks was 0/48, and schema drift count was 0.

Task outcomes were:

| Task | Cases | Main metric | Source report(s) |
| --- | ---: | --- | --- |
| SVA repair | 18 | 11/18 scaffold repair success and 11/18 final exact match; no live Jasper final proof in this evaluator | `reports/llm/codex_full_summary_20260511T015713Z.md`; `reports/llm/codex_full_error_cases_20260511T015713Z.md` |
| Triage | 30 | 28/30 issue and action accuracy | `reports/llm/codex_full_summary_20260511T015713Z.md` |
| Coverage | 9 | 9/9 gap and action accuracy; 6/6 reachable sequence presence | `reports/llm/codex_full_summary_20260511T015713Z.md` |

The full Codex table is in
`reports/final/jasperloop_dv_result_tables.md`, Table 4. This benchmark is not
a production-readiness claim and does not compare Codex with Qwen.

## 10. JasperGold Validation Results

JasperGold validation is the strongest verifier evidence in the repo, but it is
still scoped to the checked harnesses, assumptions, and generated candidates.
The primary Moore evidence report recorded 30/30 case packets with Jasper
reports and trace references. The expanded benchmark evidence report recorded
53/53 schema-valid prove-backed packets, 53 report references, 53 trace-dir
references, and 610 trace file references. It also recorded auxiliary
cover/vacuity blockers: 0/4 cover runs and 0/4 vacuity runs succeeded because
the current Jasper 2018.09 command path rejected or lacked the required
commands.

For restored Codex repair candidates, Moore/JasperGold checked 34 candidates
covering 18 repair cases: 34/34 syntax pass, 34/34 proven, 0 falsified, and 0
timeout/unknown. For the SVA repair ablation handoff, Moore/JasperGold checked
126 candidates across seven variants: 126/126 syntax pass, 126/126 proven, 0
falsified, and 0 unknown/timeout.

These results are detailed in
`reports/final/jasperloop_dv_result_tables.md`, Tables 3, 5, and 7. The proof
pass does not imply intent alignment. `not_flagged_vacuous` and
`non_vacuous_proven` are manifest interpretations, not independent explicit
non-vacuity certificates when explicit vacuity status is null or the vacuity
flow did not run.

## 11. SVA Repair Ablation Results

Stage 4A evaluated seven repair variants over the original 18 repair cases:
`baseline_prompt`, `cex_aware_prompt`, `signal_whitelist_only`,
`temporal_hint_only`, `one_round_repair`, `multi_round_repair`, and
`self_check_before_final`. Local scaffold success ranged from 12/18 to 13/18.
The sanitized handoff artifact contained 126 rows and was later checked on
Moore/JasperGold with 126/126 syntax pass and 126/126 proven.

The ablation table is in
`reports/final/jasperloop_dv_result_tables.md`, Table 6. The source reports
explicitly separate local scaffold metrics, exact-template match, selected
output proof, and best-of-candidates proof. For the committed handoff artifact,
pass@k equals pass@1 because there is one selected/final row per case per
variant. Best-of-k remains an upper-bound search metric, not single-output
success.

## 12. FVEval-Compatible Subset

The FVEval-compatible subset imported 30 cases from the NVLabs FVEval
repository at source commit `141afe7dcf03a0b86547b94657d9d610b6087724`: 10
NL2SVA-Human, 10 NL2SVA-Machine, and 10 Design2SVA. The local evaluation runner
completed all 30 cases with 30/30 syntax scaffold pass, 30/30 valid JSON,
30/30 deterministic fallback, 0/30 hallucinated signals, and 0/20
exact/reference match for reference-eligible NL2SVA cases. Jasper syntax/proof
was not run.

This is not an official FVEval reproduction. It does not reproduce FVEval's
commercial property-equivalence flow and does not run JasperGold, Codex, or
Qwen. The 30/30 fallback rate means no external predictions were supplied, not
that an LLM achieved the result. Sources:
`reports/benchmarks/fveval_subset_import_20260511T031107Z.md`,
`reports/fveval/fveval_subset_eval_summary_20260511T141418Z.md`, and
`evaluation/results/fveval_subset_results.md`.

## 13. Local Qwen 3+3+3 Subset

The local Qwen workflow subset used `Qwen/Qwen3-14B-AWQ` through a local vLLM
OpenAI-compatible endpoint at `http://127.0.0.1:8000/v1`. It completed 9 cases:
3 SVA repair, 3 triage, and 3 coverage. The workflow status was `ok`,
valid JSON was `True`, fallback count was 0, LLM error count was 0,
`LOCAL_ONLY` was `True`, cloud fallback was not allowed, and cloud fallback was
not called. The runtime-fix report recorded total latency of 15597.22 ms for
the subset.

This is local-only workflow readiness evidence. Qwen 3+3+3 is not a full Qwen
benchmark and does not support Qwen-vs-Codex comparison. Sources:
`reports/local_llm/qwen_workflow_subset_summary_20260511T202620Z.md`,
`reports/local_llm/qwen_runtime_fix_summary_20260511T202643Z.md`, and
`docs/local_qwen_workflow.md`.

## 14. Intent Alignment Evaluator

Stage 5C added a static/offline intent alignment evaluator for generated or
repaired SVA candidates. It compares candidate SVA text against available
intent metadata, reference SVA, allowed signals, and optional proof-status
context. The smoke run evaluated 18 repair candidates and produced 15
`likely_aligned`, 2 `likely_misaligned`, and 1 `partially_aligned` labels; 10
of 18 required manual review.

This evaluator is a heuristic review aid. It is not formal equivalence, not a
substitute for engineer review, and not proof that a proven property matches
the intended requirement. Proof status is recorded as context only. Sources:
`docs/intent_alignment.md`,
`reports/alignment/intent_alignment_smoke_summary_20260511T180423Z.md`, and
`reports/alignment/intent_alignment_smoke_manifest_20260511T180423Z.json`.

## 15. Limitations

The local-DV benchmark is small, even after expansion to 53 cases. Expected
issue labels and expected coverage fields are author-provided benchmark
metadata, not automatically discovered truth. Some raw artifacts, Jasper logs,
trace directories, harness dumps, and license outputs remain local-only by
policy, so the committed reports are the preserved evidence surface.

Several formal caveats are central. Proof pass does not imply intent alignment.
`not_flagged_vacuous` is not explicit non-vacuity certification. Auxiliary
cover and vacuity checks failed for the expanded benchmark evidence under the
available Jasper 2018.09 command path. Best-of-k is not single-output success.
The FVEval-compatible subset is not official FVEval reproduction. The Qwen
3+3+3 subset is not a full Qwen benchmark. Replay and dry-run workflow evidence
is not real model performance. JasperLoop-DV is not production-ready signoff
automation.

## 16. Future Work

The next technical work should keep the same evidence boundaries. Useful
extensions include larger local-DV benchmarks, matched Codex and Qwen manifests
for fair comparison, explicit Jasper-compatible cover/vacuity flows, stronger
intent-alignment checks, committed sanitized candidate/reference diffs for
failed repair cases, and an external-design harness for FVEval-compatible
Jasper or equivalence evaluation.

Workflow future work includes turning replay handoff into a live Moore/Jasper
handoff under explicit execution gates, preserving raw artifact hygiene,
improving local endpoint launch robustness, and broadening static intent
alignment beyond the current SVA repair smoke.

## 17. Claim Boundaries

The final claim boundary is:

| Area | Supported | Not supported | Source report(s) |
| --- | --- | --- | --- |
| Formal evidence | JasperGold/Moore reports support syntax/proof claims for checked candidates and packets | Proof pass does not imply intent alignment or production signoff | `reports/jasper/codex_repair_final_proof_summary_20260511T053413Z.md`; `reports/jasper/sva_repair_ablation_final_proof_summary_20260511T143254Z.md` |
| Vacuity | Reports may state not parsed or not flagged vacuous where manifests say so | `not_flagged_vacuous` is not explicit non-vacuity certification | `reports/jasper/codex_repair_final_proof_summary_20260511T053413Z.md`; `reports/jasper/sva_repair_ablation_final_proof_summary_20260511T143254Z.md`; `reports/jasper/expanded_benchmark_evidence_summary_20260511T064639Z.md` |
| Model results | Codex full benchmark and local Qwen subset are recorded in separate bounded reports | No Qwen-vs-Codex comparison is supported | `reports/llm/codex_full_summary_20260511T015713Z.md`; `reports/local_llm/qwen_workflow_subset_summary_20260511T202620Z.md` |
| External benchmark anchor | The 30-case FVEval-compatible local subset runner completed | Not official FVEval reproduction and no commercial equivalence flow | `reports/fveval/fveval_subset_eval_summary_20260511T141418Z.md`; `reports/benchmarks/fveval_subset_import_20260511T031107Z.md` |
| Workflow packaging | CLI, workflow, replay demo, local backend, and playbook guidance exist | Replay/dry-run evidence is not real model performance or production readiness | `reports/release/stage5_result_ledger_20260511T205601Z.md`; `reports/workflows/e2e_demo_summary_20260511T191259Z.md`; `reports/release/stage55_result_ledger_20260511T224417Z.md` |

The more detailed claim-boundary table is in
`reports/final/jasperloop_dv_result_tables.md`, Table 11.
