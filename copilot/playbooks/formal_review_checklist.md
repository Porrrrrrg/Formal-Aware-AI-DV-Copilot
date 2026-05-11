# Formal Review Checklist

Purpose: provide a compact review gate for formal-aware DV changes, playbooks, prompts, rules, and reports.

## Required Context

- Property intent, assertion or assumption text, and requirement trace.
- Tool status with command, inputs, commit, and artifact paths.
- Assumption and reset semantics.
- Counterexample, witness, vacuity, and coverage evidence when relevant.
- Backend and manifest identity for any model comparison.

## Checklist

| Area | Review question | Pass evidence |
| --- | --- | --- |
| Intent | Does each property still check the stated design rule? | Requirement trace and human-readable explanation |
| Syntax | Does generated SVA parse and elaborate? | Tool syntax result or parser log |
| Proof | Is proof status reported without overstating meaning? | Proof artifact and scoped claim |
| Vacuity | Is trigger reachability explicit when non-vacuity is claimed? | Cover witness or vacuity certificate |
| Assumptions | Do assumptions describe legal environment behavior only? | Owner-reviewed assumption rationale |
| CEX Debug | Are failure hypotheses tied to trace values? | Failing cycle and cited signal evidence |
| Coverage | Are unhit goals classified before recommending tests or waivers? | Coverage gap classification and action |
| Replay | Is replay described as determinism/plumbing only? | Replay manifest, no model-performance claim |
| Backend Comparison | Are Qwen/Codex comparisons based on matched manifests? | Same benchmark, prompt, schema, seed policy, and verifier config |
| Signoff | Are production signoff claims avoided? | Explicit limitation statement |

## Automatic Review Blocks

- Claiming proof pass means the design intent is satisfied.
- Claiming non-vacuity from `not_flagged_vacuous` alone.
- Comparing model quality without manifest parity.
- Treating a replay demo as a model-performance benchmark.
- Describing JasperLoop-DV as production signoff automation.
- Adding assumptions that mask legal input behavior without owner rationale.
- Waiving coverage without proof, spec rationale, and owner review.

## Minimum Closeout

- List changed properties, assumptions, coverage goals, or rules.
- List verification commands run and their results.
- List residual risks and owner review needs.
- Keep claims within the evidence boundary.
