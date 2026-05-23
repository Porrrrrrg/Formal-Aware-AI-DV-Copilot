# Stage 14 Final Research Story

This document packages the JasperLoop-DV research narrative from committed
repository evidence only. Stage 14 did not run new experiments, send external
LLM prompts, invoke JasperGold, alter benchmark labels, or change production
code.

## Core Story

JasperLoop-DV studies a practical question in AI-assisted design verification:
can an AI copilot help a DV engineer move from formal evidence to useful next
actions without treating fluent model output as proof?

The answer supported by the repository is a bounded workflow architecture. The
LLM is a proposal and summarization engine. JasperGold, replay fixtures,
schemas, manifests, and human review define the evidence boundary. The system
packages RTL, specifications, SVA, assumptions, counterexamples, coverage goals,
and formal-tool results into structured evidence packets, then asks agents to
produce repair, triage, generation, or coverage-closure recommendations.

The strongest project contribution is not a claim that an AI can replace DV
signoff. It is a demonstrated evidence discipline: every useful AI output must
name its provenance, fallback status, visible signals, formal status, and claim
boundary.

## Research Thesis

Syntax-valid SVA and plausible explanations are insufficient for formal DV
workflows. A useful copilot must separate at least four questions:

1. Did the model produce valid structured output?
2. Did the candidate stay within the visible RTL and harness context?
3. Did a formal backend actually check the property, cover, or vacuity target?
4. Does the checked property still match the engineer's intent?

JasperLoop-DV implements that separation through evidence packets, typed backend
results, replay/local/LLM provenance, and conservative final reports.

## System Contributions

| Contribution | What exists | Primary evidence |
| --- | --- | --- |
| Evidence packet boundary | Schema-validated packets connect formal evidence to agent inputs | `copilot/schemas/evidence_packet.schema.json`, `reports/jasper/expanded_benchmark_evidence_summary_20260511T064639Z.md` |
| JasperGold backend facade | Typed backend results capture syntax, proof, vacuity, counterexample paths, and tool errors | `copilot/backends/jasper_backend.py`, `tests/backends/test_jasper_backend.py` |
| DV task agents | SVA generation, SVA repair, triage, and coverage closure agents consume structured context | `copilot/agents/`, `docs/design_doc.md` |
| Workflow packaging | CLI workflows emit manifests, dry-run boundaries, Moore handoff manifests, and human-reviewable reports | `docs/workflow_usage.md`, `reports/workflows/e2e_demo_summary_20260511T191259Z.md` |
| Retrieval-assisted Design2SVA | Local RTL context builder and pass@k evaluator support deterministic, replay, LLM, and Jasper paths | `docs/design2sva_proofloop_stage5.md`, `evaluation/results/design2sva_results.md` |
| Wrapper parity diagnostics | Native reference, wrapper embedding, and antecedent reachability are separated before judging candidates | `docs/design2sva_harness_rootcause_stage11.md`, `docs/design2sva_wrapper_parity_stage12.md`, `docs/design2sva_fixed_wrapper_rerun_stage13.md` |

## Evidence Narrative

The repository starts from a formal-first principle. Local DV cases are not just
prompt rows; they include RTL, formal harnesses, assumptions, assertion
manifests, signal-role maps, coverage plans, and labeled diagnosis cases. The
expanded local-DV benchmark records 53/53 schema-valid prove-backed evidence
packets, 53 report references, 53 trace-directory references, and 610 trace file
references. Those packets are the base evidence layer.

The Codex benchmark then tests whether a model can consume structured evidence
and return valid, bounded outputs. The committed full run records 57 attempted
cases with 71/71 valid JSON outputs, 0 fallback, 0 LLM errors, and 0/48
hallucinated-signal rate for defined signal tasks. Task metrics are 11/18 SVA
repair scaffold success, 28/30 triage issue/action accuracy, and 9/9 coverage
gap/action accuracy. These are model-output and scaffold metrics, not broad
correctness claims.

Formal validation gives a stronger but narrower result. Restored Codex SVA
repair candidates were checked on Moore/JasperGold with 34/34 syntax pass and
34/34 proven over 18 repair cases. The SVA repair ablation handoff checked 126
candidates across seven variants with 126/126 syntax pass and 126/126 proven.
Those proof results are scoped to the checked harnesses, assumptions, and
properties. They do not prove intent alignment.

The workflow layer shows that this evidence discipline can be packaged for a DV
engineer. The replay demo loads a structured repair case, replays a deterministic
candidate, prepares a Moore handoff manifest, imports a sanitized verifier
sample, runs static intent alignment, and emits a report and manifest. The demo
is deliberately offline and reproducible, so it demonstrates workflow plumbing,
not live model quality or a new formal run.

The Design2SVA thread is the most important research lesson. Stage 6 produced a
negative formal result: real Codex candidates were valid JSON, syntax-clean, and
non-hallucinated, but JasperGold reported unreachable outcomes. Stage 10 and
Stage 11 then showed that even local reference assertions failed through the
Design2SVA wrapper while native benchmark references proved, isolating a wrapper
embedding problem. Stage 12 repaired wrapper parity by matching native harness
topology, property module naming, clock/reset setup, and focused report parsing.
Stage 13 reran prior committed Codex candidates through the repaired wrapper
without sending new prompts. On the measured three-case subset, the original
Codex rerun reported syntax@k/proven@k/proven_non_vacuous@k of 1.000 for k=3,
and the anti-vacuity Codex rerun reported the same for k=5. The supported claim
is that the earlier negative Design2SVA result was dominated by wrapper and
embedding issues, and that the repaired wrapper provides a fair rerun path for
the prior candidates on this subset.

## Claim Boundaries

| Area | Supported by committed evidence | Boundary |
| --- | --- | --- |
| Local formal packets | 53/53 expanded local-DV cases have schema-valid prove-backed packets | Expected labels are benchmark metadata; raw logs and traces remain local by policy |
| Codex structured output | 57-case Codex run has valid JSON, no fallback, no LLM errors, and bounded task metrics | Not a comparison to Qwen and not an unattended correctness result |
| SVA repair proof | 34 restored candidates and 126 ablation handoff candidates proved under Moore/JasperGold | Proof is scoped to checked harnesses and assumptions; intent alignment remains separate |
| Design2SVA wrapper parity | Repaired wrapper reproduces native reference behavior on measured local reference-oracle fixtures | Generalization beyond the measured subset is not shown |
| Design2SVA candidate rerun | Prior committed Codex candidates prove non-vacuously on the measured three-case fixed-wrapper reruns | No new external LLM prompts were sent; broad Design2SVA success is not shown |
| Workflow demo | Offline replay workflow emits case, candidate, handoff, verifier import, intent alignment, manifest, and report | Replay/dry-run evidence is not live model performance or a new JasperGold run |

## Paper Story In One Sentence

JasperLoop-DV shows that AI assistance for DV becomes more defensible when model
outputs are treated as evidence-indexed proposals and every claim is gated by
structured provenance, formal backend results, and explicit review boundaries.

## Recommended Reader Path

1. Read `reports/final/jasperloop_dv_final_report.md` for the Stage 6A baseline.
2. Read `evaluation/results/design2sva_results.md` for the current Design2SVA
   provenance table.
3. Read `docs/design2sva_fixed_wrapper_rerun_stage13.md` for the latest wrapper
   parity result.
4. Read `docs/final_demo_plan.md` for a bounded project demonstration script.
5. Read `docs/paper_outline.md` for the manuscript structure and precise claim
   table.
