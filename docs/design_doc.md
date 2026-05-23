# JasperLoop-DV Design Document

## Goal

JasperLoop-DV is a formal-aware AI design verification copilot. It consumes RTL, specifications, assertions, assumptions, coverage goals, and JasperGold evidence, then produces structured recommendations for assertion generation, repair, failure triage, and coverage closure.

## System Principle

The LLM is not the verification oracle. JasperGold is the source of truth for syntax, proof, counterexamples, cover reachability, and vacuity. The agent is responsible for summarizing evidence, proposing fixes, and ranking likely next actions for engineer review.

## Claim Boundary Table

| Claim | Supported Today | Unsupported Claim | Next Evidence Required |
| --- | --- | --- | --- |
| JasperGold proof | Supported only for checked harnesses, properties, assumptions, and imported JasperGold summaries | Full design signoff or intent correctness | Per-property proof, vacuity, harness, assumptions, and tool-version manifests |
| Vacuity | Vacuity status is parsed when report data exists | `not_flagged_vacuous` as an explicit non-vacuity certificate | Explicit vacuity runs with parsed property-level status |
| Codex results | Real runs may be reported only when source/error/fallback fields show Codex was used | Deterministic fallback accuracy as Codex accuracy | Valid JSON, fallback, source, error, and hallucinated-signal metrics |
| FVEval subset | Local-compatible subset plumbing and prompt-sanitization checks | Official FVEval reproduction or commercial equivalence results | FVEval-compatible harnesses and FV tool scoring |
| Replay/dry-run | Workflow and artifact-contract evidence | Model quality or new JasperGold proof | Live backend run manifests and imported formal evidence |

## Architecture

```text
RTL + Spec + SVA + Assumptions
        |
        v
JasperGold Formal Runner
        |
        v
Formal BackendResult + Evidence Extractor
        |
        v
Structured Evidence Packet + RTL Retrieval Index
        |
        +--> SVA Generation Agent
        +--> SVA Repair Agent
        +--> DV Failure Triage Agent
        +--> Coverage Closure Agent
        |
        v
JasperGold Re-check / Evaluation
```

## Evidence Packet

The evidence packet is the central interface between formal tooling and LLM reasoning. It contains:

- design identity and task type
- property or coverage goal under analysis
- assertion and assumption intent
- JasperGold proof, cover, counterexample, and vacuity results
- RTL source excerpts and signal role maps
- allowed issue labels and next actions

Counterexample summaries are role-aware. The raw VCD-derived signal events are preserved, and the packet also includes semantic events that annotate signals with manifest roles such as `client 0 request`, `client 1 grant`, or `APB write data`. This gives the LLM a compact DV explanation without hiding the formal evidence.

`copilot/backends` is the package boundary for formal tools. It exposes typed
`BackendResult` objects with syntax, proof, vacuity, counterexample path, raw
log path, and structured error fields. Prompt code should consume these typed
objects or evidence packets; it should not shell out to JasperGold directly.

`copilot/retrieval` provides ProofLoop-style local context: module interfaces,
assign drivers, always blocks, instance hierarchy, signal logic, and clock/reset
candidates. The current implementation is a robust regex fallback with optional
future `pyslang`/`slang` integration.

## Agent Modes

### Mode 1: SVA Generation

Input: RTL context plus a natural-language property intent.

Output: candidate SVA JSON containing property id, generated SVA, referenced signals, and explanation.

### Mode 2: SVA Repair

Input: failed SVA plus JasperGold feedback.

Output: repaired SVA, repair rationale, and expected JasperGold status.

Repair loop:

```text
generate -> JasperGold check -> summarize feedback -> repair -> re-check
```

### Mode 3: Failure Triage

Input: failing assertion/counterexample/assumptions/RTL context.

Output: diagnosis JSON classifying one of:

- `rtl_design_bug`
- `assertion_property_bug`
- `assumption_constraint_bug`
- `testbench_stimulus_bug`
- `reachable_coverage_gap`
- `unreachable_or_invalid_coverage_goal`

### Mode 4: Coverage Closure

Input: coverage goal, observed hit count, formal cover reachability evidence, assumptions, and related signals.

Output: coverage gap classification, recommended closure action, and directed sequence or waiver/proof recommendation.

## Benchmarks

Primary benchmark:

- 2-client round-robin arbiter
- single-entry ready/valid buffer
- tiny APB-lite register block
- 1-read/1-write FIFO

Each design has correct RTL, bug variants, assertions, assumptions, coverage goals, manifests, and labeled diagnosis cases. The current local-DV set contains 53 labeled cases across four designs, covering RTL bugs, assertion bugs, assumption bugs, testbench/stimulus bugs, reachable coverage gaps, invalid/unreachable coverage goals, vacuity cases, and false-positive-style intent traps where a property can prove but still not match the intended behavior.

## Evaluation

The main comparison is:

- heuristic baseline
- raw-log LLM
- direct SVA LLM
- structured JasperLoop-DV agent

Ablations remove assertion manifest, assumption manifest, counterexample summary, coverage plan, or repair loop.

Evaluation outputs separate deterministic scaffold/fallback behavior from real
LLM-backed rows with `source_counts`, fallback/error rates,
hallucinated-signal rates, and `output_family_counts`. Syntax pass is reported
as a scaffold metric unless backed by JasperGold proof/vacuity evidence.
