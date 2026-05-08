# Progress Report

## Current State

- Empty GitHub repository cloned locally.
- Phase 0 scaffold created.
- Benchmark, JasperGold, parser, agent, schema, and evaluation directories created.
- Initial JasperGold smoke testing on `moore` completed for arbiter, ready/valid buffer, and APB-lite.
- Evidence packet generation and schema validation were exercised on `arbiter_rr2/bug_double_grant`.
- JasperGold prove runs now dump VCD traces, including compressed traces, and evidence packets include focused counterexample summaries.

## Next Milestones

1. Add more labeled cases until the local benchmark reaches 30 diagnosis cases.
2. Add signal-role-map loading so counterexample summaries can call out design-role names.
3. Replace placeholder agents with an actual model backend and JSON repair loop.
4. Add SVA generation/repair evaluation cases.
5. Add coverage-mode witness extraction and vacuity-mode packet fields.
