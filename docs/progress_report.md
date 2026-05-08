# Progress Report

## Current State

- Empty GitHub repository cloned locally.
- Phase 0 scaffold created.
- Benchmark, JasperGold, parser, agent, schema, and evaluation directories created.
- Initial JasperGold smoke testing on `moore` completed for arbiter, ready/valid buffer, and APB-lite.
- Evidence packet generation and schema validation were exercised on `arbiter_rr2/bug_double_grant`.
- JasperGold prove runs now dump VCD traces, including compressed traces, and evidence packets include focused counterexample summaries.
- Signal role maps are loaded into evidence packets, and counterexample summaries now include semantic role-annotated events.
- Primary benchmark expanded to 30 labeled cases across arbiter, ready/valid buffer, and APB-lite.
- Added `scripts/build_all_evidence_packets.py` to generate evidence packets for all labeled cases.

## Next Milestones

1. Replace placeholder agents with an actual model backend and JSON repair loop.
2. Add SVA generation/repair evaluation cases.
3. Add coverage-mode witness extraction and vacuity-mode packet fields.
4. Expand semantic counterexample heuristics for ready/valid and APB-specific failures.
5. Run the 30-case benchmark through heuristic, raw-log, and structured-agent baselines.
