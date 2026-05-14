# Paper Outline: JasperLoop-DV

Working title: "JasperLoop-DV: Evidence-Centered LLM Assistance for Formal
Design Verification Workflows"

This outline is based on committed repository evidence only. Stage 14 did not
send external LLM prompts, rerun JasperGold, rerun Moore, relabel benchmarks, or
modify source code.

## Abstract

Large language models can help write assertions, summarize counterexamples, and
recommend verification actions, but their outputs are not formal evidence.
JasperLoop-DV is a research prototype for evidence-centered AI assistance in
design verification. The system packages RTL, specifications, assertions,
assumptions, coverage goals, and JasperGold results into schema-validated
evidence packets, then routes those packets to agents for SVA generation, SVA
repair, failure triage, and coverage closure. Across committed local-DV
evidence, the expanded benchmark records 53/53 schema-valid prove-backed
packets. A Codex benchmark records 57 attempted cases with 71/71 valid JSON
outputs, 0 fallback, and task metrics of 11/18 SVA repair scaffold success,
28/30 triage issue/action accuracy, and 9/9 coverage action accuracy. Restored
repair candidates and ablation handoff candidates were checked on
Moore/JasperGold with 34/34 and 126/126 proven outcomes respectively, scoped to
their checked harnesses and assumptions. The Design2SVA case study shows why
wrapper parity matters: after isolating a wrapper embedding bug, prior committed
Codex candidates proved non-vacuously on the measured three-case fixed-wrapper
reruns without sending new prompts. The paper argues for provenance-first DV
copilot evaluation: structured output quality, formal proof status, vacuity or
reachability evidence, and intent alignment must be reported separately.

## Introduction

Problem:

- DV engineers operate over RTL, specs, SVA, assumptions, counterexamples,
  coverage goals, tool logs, and review rules.
- LLMs can propose useful artifacts, but plausible SVA and confident
  explanations can be wrong, weak, vacuous, or unsupported by the harness.
- A practical copilot must preserve the difference between a candidate, a
  verifier result, and an engineer-reviewed conclusion.

Thesis:

- Evidence-centered workflow design makes LLM assistance more useful and more
  auditable for formal DV tasks.
- The model should consume formal evidence and propose next actions; JasperGold
  and structured manifests should bound formal claims.

Contributions:

1. A schema-validated evidence packet architecture for DV agent inputs.
2. A typed JasperGold backend facade and artifact policy for formal provenance.
3. Four agent workflows: SVA generation, SVA repair, failure triage, and
   coverage closure.
4. Evaluation infrastructure separating deterministic fallback, replay, real
   LLM, and measured formal rows.
5. A Design2SVA wrapper parity case study showing how harness bugs can dominate
   apparent model failures.
6. A conservative claim table that separates supported, partially supported, and
   unsupported statements.

## Related Work

FVEval:

- Motivates evaluating generated SVA with formal tools instead of text match or
  syntax alone.
- JasperLoop-DV adopts formal-tool evaluation and records syntax, proof,
  vacuity, reachability, fallback, and source provenance where available.
- The repository includes a 30-case FVEval-compatible local subset runner, but
  it is not an official FVEval reproduction and does not reproduce commercial
  equivalence scoring.

ProofLoop:

- Motivates RTL/formal context retrieval plus iterative solver feedback.
- JasperLoop-DV adopts the feedback-loop direction for repair and Design2SVA,
  using local RTL retrieval and JasperGold feedback when checks run.
- The project does not claim ProofLoop-level performance; it extends the idea
  toward broader DV workflow tasks.

LLM-assisted DV positioning:

- The paper should position JasperLoop-DV as a workflow copilot, not AI RTL
  generation and not pure assertion synthesis.
- The differentiated task is ownership recommendation: RTL bug, assertion bug,
  assumption bug, testbench/stimulus issue, reachable coverage gap, or invalid
  coverage goal.

## System Design

Pipeline:

```text
RTL + spec + SVA + assumptions + coverage goals
        |
        v
JasperGold runner or replay backend
        |
        v
Typed BackendResult + parsers + trace summaries
        |
        v
EvidencePacket + RTL retrieval context
        |
        +--> SVA generation agent
        +--> SVA repair agent
        +--> DV failure triage agent
        +--> Coverage closure agent
        |
        v
Workflow manifest, candidate JSON, report, and optional JasperGold re-check
```

Key design choices:

- Agents produce structured JSON, not free-form final authority.
- Backend/source/fallback/error fields are first-class evaluation metrics.
- Deterministic scaffold, replay, local LLM, hosted LLM, and formal measured
  outputs are never collapsed into one score.
- Dry-run workflow defaults prevent accidental external sends.
- Static intent alignment is reported separately from proof status.

## Evidence Packet Architecture

Packet contents:

- design identity, task type, case ID, property or coverage goal;
- assertion, assumption, and coverage intent;
- RTL excerpts, module interface, clock/reset candidates, signal-role maps;
- JasperGold syntax/proof/cover/counterexample/vacuity fields when available;
- counterexample summaries with role-aware signal descriptions;
- allowed issue labels and allowed next actions;
- artifact references and schema version.

Why it matters:

- The evidence packet makes the LLM context compact but auditable.
- It prevents benchmark answer leakage by separating prompt-visible context from
  expected labels.
- It gives evaluators a stable boundary for hallucinated-signal checks,
  fallback accounting, and source-family reporting.

Evidence:

- `copilot/schemas/evidence_packet.schema.json`
- `tools/build_evidence_packet.py`
- `reports/jasper/moore_evidence_summary_20260511T004654Z.md`
- `reports/jasper/expanded_benchmark_evidence_summary_20260511T064639Z.md`

## JasperGold Backend

Backend role:

- JasperGold is the formal oracle only for checks that actually run.
- The backend facade records syntax status, proof status, vacuity status,
  counterexample paths, raw report references, parser errors, and structured
  artifact paths.
- Workflow and evaluation code consume typed backend results rather than
  scraping ad hoc logs inside prompts.

Measured evidence:

- 53/53 expanded local-DV packets are schema-valid and prove-backed.
- 34/34 restored Codex SVA repair candidates syntax-pass and prove.
- 126/126 SVA repair ablation handoff candidates syntax-pass and prove.
- Stage 13 fixed-wrapper Design2SVA reruns record measured formal status for
  three local cases.

Backend caveats:

- Proof is scoped to a checked harness, assumptions, property, bound, and tool
  configuration.
- A proof pass does not establish semantic intent alignment.
- `not_flagged_vacuous` must not be reinterpreted as an independent explicit
  non-vacuity certificate unless the relevant run records explicit support.
- Auxiliary cover/vacuity flows had command-path blockers in earlier expanded
  evidence under the available Jasper 2018.09 setup.

## Design2SVA Wrapper Parity Lesson

Research question:

- When Design2SVA candidates fail formal checks, is the failure caused by model
  generation, wrapper embedding, native harness setup, reset/clock reachability,
  or assertion semantics?

Stage progression:

| Stage | Observation | Lesson |
| --- | --- | --- |
| Stage 6 | Real Codex candidates were valid JSON, syntax-clean, non-hallucinated, but JasperGold reported unreachable outcomes | Syntax and signal validity are not enough |
| Stage 10 | Local reference-oracle assertions also failed in the Design2SVA wrapper | Candidate quality was not yet isolated |
| Stage 11 | Native benchmark references proved while the same references failed through the wrapper | Wrapper/embedding was the main suspect |
| Stage 12 | Wrapper topology was repaired to match native harness behavior | Reference parity became measurable |
| Stage 13 | Prior committed Codex candidates were rerun through the fixed wrapper without new prompts | Earlier negative results were dominated by wrapper issues on the measured subset |

Measured Stage 13 result:

- Original Codex fixed-wrapper rerun: 3 cases, k=3, syntax@k=1.000,
  proven@k=1.000, proven_non_vacuous@k=1.000, valid_json_rate=1.000,
  fallback_rate=0.000, hallucinated_signal_rate=0.000.
- Anti-vacuity Codex fixed-wrapper rerun: 3 cases, k=5, syntax@k=1.000,
  proven@k=1.000, proven_non_vacuous@k=1.000, valid_json_rate=1.000,
  fallback_rate=0.000, hallucinated_signal_rate=0.000.
- Reference-oracle fixed-wrapper sanity: 3 cases, k=1, wrapper_parity_pass_rate
  1.000 and root-cause detail `reference_oracle_matches_native_formal_behavior=3`.

Claim:

- Supported: the repaired wrapper enables a fair measured rerun path for prior
  committed Codex Design2SVA candidates on the local three-case subset.
- Not supported: broad Design2SVA success or generalization beyond the measured
  subset.

## Evaluation

Benchmarks and evidence sets:

- Local-DV benchmark: `apb_regblock`, `arbiter_rr2`, `fifo_1r1w`, `rv_buffer`;
  53 current labeled cases after expansion.
- Codex full benchmark: 57 cases covering SVA repair, triage, and coverage.
- SVA repair final proof: 34 restored Codex repair candidates over 18 cases.
- SVA repair ablation handoff: 126 candidates from seven variants over 18 cases.
- FVEval-compatible subset: 30 local imported cases, deterministic fallback only.
- Qwen local 3+3+3 subset: 9 workflow readiness cases through a local endpoint.
- Design2SVA fixed-wrapper reruns: measured three-case local subset.

Metrics:

- valid JSON rate;
- fallback rate;
- LLM error rate;
- hallucinated-signal rate;
- syntax@1 and syntax@k;
- proven@1 and proven@k;
- non_vacuous@k or proven_non_vacuous@k when measured;
- triage issue/action accuracy;
- coverage gap/action accuracy;
- source counts and output family counts;
- root-cause and failure-category counts.

Main results to report:

- Expanded local-DV: 53/53 schema-valid prove-backed packets.
- Codex full: 71/71 valid JSON, 0 fallback, 0 LLM errors.
- Codex task outcomes: 11/18 repair scaffold success, 28/30 triage
  issue/action accuracy, 9/9 coverage gap/action accuracy.
- Repair final proof: 34/34 syntax pass and 34/34 proven.
- Repair ablation proof: 126/126 syntax pass and 126/126 proven.
- Design2SVA fixed-wrapper reruns: measured three-case k=3 and k=5 subsets with
  proven_non_vacuous@k=1.000.

## Ablation

SVA repair ablation:

- Seven variants: `baseline_prompt`, `cex_aware_prompt`,
  `signal_whitelist_only`, `temporal_hint_only`, `one_round_repair`,
  `multi_round_repair`, and `self_check_before_final`.
- Local scaffold success ranged from 12/18 to 13/18.
- The committed handoff artifact contained 126 rows and later checked
  126/126 syntax pass and 126/126 proven on Moore/JasperGold.
- pass@k equals pass@1 for the committed handoff because each case/variant has
  one selected final row.

Design2SVA diagnostic ablation:

- Stage 6 compared LLM-only cleanliness against measured Jasper results and
  showed unreachable outcomes were formal failures.
- Stage 10-12 separated native reference, wrapper embedding, reset/post-reset
  reachability, antecedent reachability, and candidate assertion proof.
- The ablation lesson is methodological: wrapper parity and reachability checks
  must precede model-quality interpretation.

Future ablations to include:

- Remove RTL retrieval context.
- Remove signal whitelist enforcement.
- Remove formal feedback from repair.
- Remove counterexample summaries.
- Compare one-shot candidate generation with reachability-aware repair.

## Limitations

- The benchmark is small and locally curated.
- Expected labels are benchmark metadata, not automatically discovered truth.
- Some raw Jasper logs, waveforms, trace trees, and generated harness dumps are
  intentionally not committed.
- The FVEval-compatible subset is not an official FVEval reproduction.
- The Qwen 3+3+3 result is local workflow readiness evidence, not a full Qwen
  benchmark and not a comparison with Codex.
- Static intent alignment is a heuristic review aid, not formal equivalence.
- Best-of-k is an upper-bound candidate search metric, not single-output
  success.
- Three-case Design2SVA fixed-wrapper results do not establish broad
  generalization.
- Proof results are scoped to checked harnesses, assumptions, and properties.

## Future Work

- Expand measured benchmarks across more RTL families, property classes, and
  bug types.
- Add explicit Jasper-compatible cover and vacuity flows with property-level
  parsed status.
- Run matched Codex and local-model evaluations with identical prompts, cases,
  and formal rerun gates.
- Add stronger intent-alignment evaluation, ideally with formal equivalence or
  mutation-based checks where feasible.
- Preserve sanitized candidate/reference diffs for failed repair and
  Design2SVA cases.
- Build an external-design evaluation path that keeps FVEval-compatible
  boundaries and avoids answer leakage.
- Improve artifact packaging for reproducible Moore/Jasper handoff while
  keeping raw logs and machine-local outputs out of git.

## Precise Claim Table

| Status | Claim | Current evidence | Evidence required next |
| --- | --- | --- | --- |
| Supported | JasperLoop-DV has an evidence-centered architecture with typed packets, backend results, agents, workflow manifests, and bounded reports | `docs/design_doc.md`, `docs/architecture_agentic_refactor.md`, schemas, tests, workflow docs | Larger user study or external replication to assess usability |
| Supported | Expanded local-DV evidence contains 53/53 schema-valid prove-backed packets | `reports/jasper/expanded_benchmark_evidence_summary_20260511T064639Z.md` | Commit or archive broader sanitized evidence across more designs |
| Supported | Codex full benchmark produced structured outputs with 71/71 valid JSON, 0 fallback, and 0 LLM errors | `reports/llm/codex_full_summary_20260511T015713Z.md` | Matched rerun with current prompts and formal re-check for every generated SVA |
| Supported | SVA repair restored candidates prove under the checked Moore/JasperGold harnesses | `reports/jasper/codex_repair_final_proof_summary_20260511T053413Z.md` with 34/34 proven | Explicit intent-equivalence or stronger manual review evidence per candidate |
| Supported | SVA repair ablation handoff candidates prove under checked Moore/JasperGold harnesses | `reports/jasper/sva_repair_ablation_final_proof_summary_20260511T143254Z.md` with 126/126 proven | Compare variants on independent held-out cases with explicit vacuity status |
| Supported | Replay workflow demonstrates local artifact plumbing without external services | `docs/demo_script.md`, `reports/workflows/e2e_demo_summary_20260511T191259Z.md` | Live backend run under explicit approval plus imported formal result |
| Supported | Design2SVA wrapper parity repair fixed the reference embedding path on the measured local subset | `docs/design2sva_wrapper_parity_stage12.md`, `evaluation/results/design2sva_eval_reference_oracle_parity_jasper.json`, fixed-wrapper sanity result | More native/reference fixtures and independent wrapper audit cases |
| Supported | Prior committed Codex Design2SVA candidates prove non-vacuously on the measured three-case fixed-wrapper reruns | `docs/design2sva_fixed_wrapper_rerun_stage13.md`, `evaluation/results/design2sva_eval_codex_fixed_wrapper_rerun.json`, `evaluation/results/design2sva_eval_antivacuity_codex_fixed_wrapper_rerun.json` | Fresh held-out Design2SVA generation with no reference leakage and measured Jasper reruns |
| Partially supported | The copilot can improve DV triage and coverage-closure recommendations | Codex full benchmark records 28/30 triage issue/action accuracy and 9/9 coverage gap/action accuracy | Larger blind benchmark, multiple designs, and reviewer adjudication |
| Partially supported | Static intent alignment can help prioritize review | Smoke run produced labels and manual-review flags over 18 repair candidates | Correlate labels with expert review and formal equivalence or mutation tests |
| Partially supported | Local Qwen backend plumbing is usable for bounded workflows | 9-case Qwen 3+3+3 local subset completed with valid JSON and no fallback | Full matched local-model benchmark with same cases and formal checks |
| Partially supported | FVEval-compatible infrastructure can host local subset experiments | 30-case local deterministic subset completed with no answer leakage | Official reproduction path or equivalent formal/equivalence scoring, if allowed |
| Unsupported | JasperLoop-DV provides unattended production signoff | No committed evidence claims this; docs explicitly bound proof and workflow evidence | Would require industrial signoff methodology, exhaustive review, tool qualification, and project-specific approval outside this repo |
| Unsupported | JasperGold proof pass proves semantic intent alignment | Intent alignment docs explicitly separate proof from intent | Property equivalence, expert review, mutation testing, or spec-to-property validation |
| Unsupported | `not_flagged_vacuous` is always an explicit non-vacuity certificate | Reports warn that some statuses are parser/report interpretations | Property-level explicit vacuity runs with parsed tool support |
| Unsupported | Broad Design2SVA success is established | Current strongest measured result is a three-case fixed-wrapper subset | Larger held-out Design2SVA benchmark with fresh prompts and measured formal outcomes |
| Unsupported | Qwen-vs-Codex comparison is supported | Qwen evidence is only a local 3+3+3 readiness subset | Matched model comparison with identical prompts, cases, decoding, and formal evaluation |
| Unsupported | FVEval official reproduction is complete | Local FVEval-compatible subset does not run official commercial equivalence flow | Official benchmark environment and scoring protocol, if accessible and approved |
