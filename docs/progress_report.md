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
- Added an 18-case SVA repair benchmark with injected syntax, unknown-signal, reset, overbroad, and temporal/semantic assertion bugs.
- Added a three-round SVA repair runner that feeds JasperGold syntax/proof/vacuity feedback back into the repair agent.
- Added a Codex CLI JSON adapter so `JASPERLOOP_LLM_CMD` can point directly at Codex for non-interactive local experiments.
- On `moore`, the full 18-case SVA repair benchmark passes JasperGold re-check with 100% final repair success and 1.0 average rounds to success in deterministic fallback mode.
- The Codex-backed repair path now records `source` and `llm_error` per repair action; the local smoke run reached Codex CLI, but the current account is usage-limited until May 10, 2026 2:40 PM, so the runner correctly fell back to the structured repair path.
- Evidence packets now enrich coverage cases with coverage-plan intent/expression fields, structured coverage evidence, and a vacuity context.
- Added a dedicated coverage-closure evaluation runner for reachable-gap vs invalid/unreachable-goal handling.
- Codex CLI health check works when network access is allowed. Added an explicit opt-in wrapper for Codex-backed SVA repair, triage, and coverage experiments so benchmark content is not sent externally without acknowledgement.
- The Codex wrapper healthcheck now passes end to end through `scripts/run_codex_llm_eval.py --task healthcheck`; benchmark subset execution is gated behind `--acknowledge-external-send`.
- Added a local Codex prompt preview/audit tool so SVA repair, triage, and coverage prompts can be inspected before external submission.
- Triage and coverage evaluation now track output source, fallback rate, LLM error rate, and hallucinated suspect-signal rate for future Codex-backed experiments.
- Added `scripts/refresh_eval_results.py` to regenerate the scaffold markdown result tables from the current evaluation runners.

## Next Milestones

1. Run `scripts/run_codex_llm_eval.py --task sva_repair --limit 3 --acknowledge-external-send` after approving external prompt export and compare against the deterministic structured fallback.
2. Use the same Codex wrapper for `triage` and `coverage` subsets, then scale to the full benchmark if JSON validity and signal hallucination rates are acceptable.
3. Add repair-loop ablations, especially no-Jasper-feedback vs Jasper-feedback repair.
4. Add real JasperGold cover witness trace dumps for coverage goals and feed those traces into `coverage_evidence.witness_events`.
5. Expand semantic counterexample heuristics for ready/valid and APB-specific failures.
