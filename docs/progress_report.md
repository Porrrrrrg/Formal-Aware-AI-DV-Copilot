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
- Added a 27-case local SVA generation property-intent set across arbiter, ready/valid buffer, and APB-lite.
- Added direct and structured SVA generation systems plus `evaluation/run_sva_eval.py`.
- Added JasperGold re-check for generated SVA candidates, including temporary generated property/harness files, prove reports, trace dumps, and vacuity reports.
- On `moore`, all 27 direct and 27 structured generated SVA candidates pass JasperGold syntax/proof re-check in the deterministic scaffold.

## Next Milestones

1. Add SVA repair cases with injected syntax/signal/temporal errors.
2. Implement the three-round JasperGold-in-the-loop SVA repair runner.
3. Connect a hosted or local LLM wrapper and run `raw_log` vs `structured` prompting with the same evaluation runner.
4. Add coverage-mode witness extraction and vacuity-mode packet fields.
5. Expand semantic counterexample heuristics for ready/valid and APB-specific failures.
