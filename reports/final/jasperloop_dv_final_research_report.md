# JasperLoop-DV Final Research Report

Stage 18 packages the final research documentation from committed artifacts
only. It does not send external LLM prompts, run new JasperGold experiments,
change benchmark labels, or reinterpret dry-run rows as formal evidence.

Companion indices and demo material:

- [Result index](result_index.md)
- [Final claim boundary](../../docs/final_claim_boundary.md)
- [Final demo script](../../docs/final_demo_script.md)
- [Reproducibility checklist](../../docs/reproducibility_checklist.md)

## Abstract

JasperLoop-DV is a research prototype for formal-aware AI assistance in design
verification. The central rule is that the LLM is not the verification oracle:
LLM outputs are candidate assertions, repairs, diagnoses, summaries, and next
actions, while JasperGold is the formal oracle when syntax, proof,
counterexample, cover, and vacuity checks are actually run.

The strongest measured Design2SVA result is bounded to the local expanded
12-case benchmark. After Stage 15 native and wrapper reference-oracle gates
passed, Stage 16 real Codex generation produced 36/36 valid JSON,
syntax-clean, non-fallback candidates for 12 cases with `k = 3`. JasperGold
replay of those exact candidates reported `proven@1 = 0.75`,
`proven@k = 1.0`, `non_vacuous@k = 1.0`, and
`proven_non_vacuous@k = 1.0`. This is local research evidence, not production
signoff automation, not arbitrary-RTL generalization, and not official FVEval
reproduction.

## 1. Introduction And Motivation

DV engineers work across RTL, specifications, assertions, assumptions,
counterexamples, coverage goals, formal-tool logs, and review checklists. LLMs
can help summarize and propose repairs, but fluent text and plausible SVA are
not proof. JasperLoop-DV studies how a copilot can help a DV engineer move from
formal evidence to useful next actions while keeping all correctness claims
tied to measured artifacts and human review.

The project contribution is an evidence discipline: model outputs carry
provenance, fallback status, visible-signal grounding, formal status, and claim
boundaries. A candidate is useful only after the relevant evidence layer says
what was generated, what was checked, and what remains unchecked.

## 2. Problem: Why LLM-Generated SVA Is Not Enough

LLM-generated SVA can fail in ways that syntax checks alone do not catch:

- It can reference unavailable signals or helper code outside the wrapper
  policy.
- It can use the right signals with the wrong temporal relation.
- It can prove only because the antecedent is unreachable or an assumption
  overconstrains the design.
- It can pass under one wrapper or harness and fail under the native benchmark
  flow.
- It can prove a property that is not the engineer's intended requirement.

JasperLoop-DV therefore separates `valid_json_rate`, `syntax@k`,
`proven@k`, reachability, vacuity, wrapper parity, and intent review. Stage 16
shows why this separation matters: all 36 real Codex candidates were valid JSON
and syntax-clean, but only the JasperGold replay row supports the formal
`proven@*` and non-vacuity metrics.

## 3. Related Work: FVEval, ProofLoop, LLM-Assisted SVA Generation

FVEval motivates evaluating generated SVA with formal tools rather than text
similarity alone. JasperLoop-DV adopts that formal-tool evaluation principle,
but the current repository evidence is not an official FVEval reproduction and
does not reproduce FVEval's commercial equivalence flow.

ProofLoop motivates iterative use of solver feedback and design context for
assertion generation. JasperLoop-DV adopts the feedback-loop direction through
typed JasperGold backend results, replayed candidate evaluation, retrieval
context, and repair loops. It does not claim ProofLoop-level performance.

LLM-assisted SVA generation is treated here as one DV workflow surface, not the
entire goal. The same evidence-packet boundary also supports SVA repair,
failure triage, assumption/vacuity debugging, coverage-closure recommendations,
and Moore/JasperGold handoff packaging.

## 4. JasperLoop-DV System Design

The system architecture is:

```text
RTL + spec + SVA + assumptions + coverage goals
        |
        v
JasperGold runner or committed replay evidence
        |
        v
typed backend result and parsers
        |
        v
schema-validated evidence packet
        |
        +--> SVA generation agent
        +--> SVA repair agent
        +--> DV failure triage agent
        +--> coverage closure agent
        |
        v
candidate JSON, handoff manifests, result ledgers, and review reports
```

The implementation separates formal-tool evidence, retrieval context, prompt
construction, backend provenance, and evaluation reporting. Local deterministic
and replay modes are kept separate from real LLM rows. JasperGold-measured rows
are the only rows that should be cited for proof and non-vacuity outcomes.

## 5. Evidence Packet And JasperGold Backend

The evidence packet is the central boundary between formal artifacts and model
reasoning. It records design identity, task type, property or coverage intent,
assumptions, role-aware signal summaries, JasperGold proof or counterexample
context where available, allowed issue labels, and allowed next actions. It
intentionally excludes expected labels and hidden reference answers from prompt
visible content.

The JasperGold backend facade records syntax, proof status, vacuity status when
available, counterexample or trace references, cover status, tool errors, and
debug artifact paths. Raw JasperGold logs, traces, waveforms, generated harness
trees, and license outputs stay out of git by policy. Sanitized JSON summaries
and markdown reports are the committed evidence surface.

## 6. Design2SVA Wrapper Parity Lesson

The most important Design2SVA lesson was not a model prompt trick. Earlier
stages found that native benchmark references could prove while the same
reference assertions failed through the Design2SVA wrapper. That meant
generated-candidate quality could not be interpreted fairly: the wrapper itself
was a confound.

Stage 12 repaired wrapper parity by aligning wrapper topology, property module
naming, clock/reset setup, bind structure, and focused report parsing. Stage 15
then used expanded native and wrapper oracle gates before any Stage 16 LLM
result was cited. The wrapper reference oracle proved 12/12 references
non-vacuously, and the native reference oracle proved 12/12 references in the
native benchmark flow.

The lesson is general for this prototype: candidate proof metrics are
meaningful only after the harness and wrapper can prove their own reference
properties.

## 7. Evaluation Setup

The final package uses committed artifacts only:

| Evidence row | Artifact | Status |
| --- | --- | --- |
| Native expanded oracle | `evaluation/results/design2sva_native_oracle_expanded_jasper.json` | JasperGold measured control |
| Wrapper expanded oracle | `evaluation/results/design2sva_reference_oracle_expanded_jasper.json` | JasperGold measured control |
| Real Codex generation | `evaluation/results/design2sva_eval_codex_expanded_subset.json` | Real LLM outputs, formal status `not_run` |
| JasperGold replay | `evaluation/results/design2sva_eval_codex_expanded_jasper.json` | JasperGold-measured replay of exact Codex candidates |
| Ablation ledger | `evaluation/results/design2sva_ablation_results.md` | Committed-artifact summary with placeholders clearly marked `not_run` |

The benchmark contains 12 local Design2SVA cases, with three cases each from
`apb_regblock`, `arbiter_rr2`, `fifo_1r1w`, and `rv_buffer`. Stage 16 uses
`k = 3` candidates per case. The prompt audit covers 12 prompts and reports no
reference SVA, no expected proof status, no exact reference SVA text, and no
Jasper evidence in the prompt.

## 8. Main Results

The headline Stage 16 result is:

| Metric | Value | Interpretation |
| --- | ---: | --- |
| Cases | 12 | Local expanded Design2SVA fixture set |
| Candidates | 36 | Real Codex outputs, `k = 3` |
| `valid_json_rate` | 1.0 | All generated rows were schema-valid |
| `fallback_rate` | 0.0 | No structured fallback rows |
| `syntax@1` / `syntax@k` | 1.0 / 1.0 | All generated candidates were syntax-clean |
| `proven@1` | 0.75 | 9/12 first candidates proved in the first round |
| `proven@k` | 1.0 | 12/12 cases had at least one proving candidate among three |
| `non_vacuous@k` | 1.0 | k=3 yielded non-vacuous proof evidence for every case |
| `proven_non_vacuous@k` | 1.0 | Final candidate paths reached proven non-vacuous outcomes |

The real Codex generation artifact by itself does not support proof claims
because formal metrics are `not_run`. The JasperGold replay artifact is the
formal measurement row because it replays the exact saved candidates through
the repaired wrapper.

## 9. Ablations And Error Analysis

Stage 17 created an ablation ledger from committed artifacts only. The measured
rows show:

- Reference and native oracle controls pass on the 12-case set.
- The current Codex Design2SVA row reaches `proven@1 = 0.75` and
  `proven_non_vacuous@k = 1.0`.
- Older fixed-wrapper rerun controls on the three-case subset also reach
  `proven_non_vacuous@k = 1.0`.
- Deterministic scaffold and local replay rows validate plumbing only.
- Direct-prompt, no-retrieval, and no-anti-vacuity component ablations are
  placeholders marked `not_run`.

The Stage 16 error analysis identifies the first-candidate gap: 9 cases solved
at k=1, while three needed later candidates among k=3. Seven intermediate rows
had `unreachable_cover_goal` diagnostics, classified as `cover_generation_bug`,
but final repaired candidate paths reached `proven_non_vacuous`. The failure
pattern is a reminder that pass@k, wrapper parity, reachability diagnostics,
and feedback repair must be reported separately.

## 10. Limitations

JasperLoop-DV is a research prototype, not production signoff automation. The
strongest Design2SVA result is on a local 12-case benchmark, not arbitrary RTL.
The benchmark is small, fixtures are authored, and expected labels are
benchmark metadata rather than automatically discovered truth.

JasperGold proof is scoped to the checked RTL, harness, assumptions, property,
tool version, and wrapper path. A proof pass does not prove semantic intent
alignment. `not_flagged_vacuous` must not be treated as an independent explicit
non-vacuity certificate unless the artifact records such a check. FVEval
compatibility infrastructure exists, but this package is not official FVEval
reproduction unless that benchmark is separately run under its own protocol.

## 11. Future Work

The next evidence steps should preserve the same boundaries:

- Run matched component ablations for direct prompting, retrieval context,
  reachability guidance, feedback repair, and candidate sampling.
- Increase the Design2SVA case count and design diversity.
- Add stronger explicit vacuity and cover flows where supported by the
  available JasperGold version.
- Strengthen intent-alignment evaluation with expert review, mutation tests, or
  equivalence-style checks.
- Run a separately documented official FVEval reproduction only if the required
  flow, licenses, inputs, and comparison criteria are available.

## 12. Reproducibility Checklist

Minimum local checks from a clean checkout:

```powershell
python --version
python -m pytest -q
python -m ruff check .
python scripts/export_codex_prompts.py --task design2sva --design2sva-cases benchmarks/design2sva_cases.json --limit 12 --design2sva-context-budget 24 --out-dir evaluation/prompt_previews/design2sva_expanded --audit-markdown evaluation/prompt_previews/design2sva_expanded_prompt_audit.md --require-no-gold-labels
python evaluation/run_design2sva_eval.py --limit 12 --k 3 --replay evaluation/results/design2sva_eval_codex_expanded_subset.json --out evaluation/results/design2sva_codex_replay_expanded_local.json
python scripts/refresh_eval_results.py --allow-rebuild-packets
```

Moore/JasperGold reruns are optional and environment-dependent. They must be
kept separate from the local quick demo and should use the commands listed in
`docs/stage16_moore_commands.md` or `docs/final_demo_script.md`.

Supported claims:

- JasperLoop-DV is a research prototype for evidence-indexed DV assistance.
- On the local 12-case Design2SVA benchmark, with Stage 15 oracle gates passing,
  Stage 16 reached `proven@1 = 0.75`, `proven@k = 1.0`,
  `non_vacuous@k = 1.0`, and `proven_non_vacuous@k = 1.0`.
- The prompt audit supports the no-gold-in-prompt guarantee for the expanded
  prompt previews.
- Wrapper parity was necessary before generated candidates could be judged.

Unsupported claims:

- Production signoff, deployment readiness, or unattended verification.
- Arbitrary RTL generalization beyond the measured local fixtures.
- Official FVEval reproduction.
- ProofLoop-level performance.
- A claim that one Codex sample is sufficient.
- A claim that syntax-valid SVA is equivalent to formally useful SVA.
