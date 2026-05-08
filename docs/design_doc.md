# JasperLoop-DV Design Document

## Goal

JasperLoop-DV is a formal-aware AI design verification copilot. It consumes RTL, specifications, assertions, assumptions, coverage goals, and JasperGold evidence, then produces structured recommendations for assertion generation, repair, failure triage, and coverage closure.

## System Principle

The LLM is not the verification oracle. JasperGold is the source of truth for syntax, proof, counterexamples, cover reachability, and vacuity. The agent is responsible for summarizing evidence, proposing fixes, and ranking likely next actions for engineer review.

## Architecture

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

## Evidence Packet

The evidence packet is the central interface between formal tooling and LLM reasoning. It contains:

- design identity and task type
- property or coverage goal under analysis
- assertion and assumption intent
- JasperGold proof, cover, counterexample, and vacuity results
- RTL source excerpts and signal role maps
- allowed issue labels and next actions

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

Each design has correct RTL, bug variants, assertions, assumptions, coverage goals, manifests, and labeled diagnosis cases.

## Evaluation

The main comparison is:

- heuristic baseline
- raw-log LLM
- direct SVA LLM
- structured JasperLoop-DV agent

Ablations remove assertion manifest, assumption manifest, counterexample summary, coverage plan, or repair loop.
