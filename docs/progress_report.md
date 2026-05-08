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
- On `moore`, all 30 cases now build evidence packets with Jasper reports and trace directories available.
- Added a model-agnostic LLM command backend via `JASPERLOOP_LLM_CMD`.
- Added formal-aware DV triage and coverage-closure agent entrypoints with deterministic structured fallbacks.
- Added `evaluation/run_agent_eval.py` to run the 30-case benchmark through the current agent scaffold without exposing gold labels to the agent input.
- Added deterministic `heuristic`, `raw_log`, and `structured` evaluation systems behind one runner.
- Added triage ablations for assertion context, assumption context, Jasper counterexample summaries, coverage context, and minimal packets.

## Next Milestones

1. Connect a hosted or local LLM wrapper and run `raw_log` vs `structured` prompting with the same evaluation runner.
2. Add SVA generation/repair evaluation cases.
3. Add coverage-mode witness extraction and vacuity-mode packet fields.
4. Expand semantic counterexample heuristics for ready/valid and APB-specific failures.
5. Add SVA repair-loop ablations after generated SVA cases exist.
