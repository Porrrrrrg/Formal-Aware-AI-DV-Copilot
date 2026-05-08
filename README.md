# JasperLoop-DV

**A JasperGold-in-the-loop AI Design Verification Agent for SVA Generation, Repair, Failure Triage, and Coverage Closure**

JasperLoop-DV is a formal-aware AI DV copilot. It does not replace JasperGold or human signoff. It wraps RTL, specs, SVA, assumptions, coverage goals, and JasperGold evidence into structured context so an LLM can help a DV engineer generate assertions, repair properties, triage failures, and recommend coverage closure actions.

```text
RTL + spec + properties + assumptions + JasperGold evidence
-> structured formal/DV context
-> LLM agent
-> SVA generation / repair / failure diagnosis / coverage closure recommendation
-> JasperGold re-check
```

## Agent Modes

1. **SVA Generation**: RTL + natural-language property intent -> candidate SVA.
2. **SVA Repair**: failed SVA + JasperGold syntax/proof/vacuity feedback -> repaired assertion.
3. **Failure Triage**: failing assertion/counterexample/assumptions/RTL context -> root-cause diagnosis.
4. **Coverage Closure**: coverage hole + formal cover/reachability evidence -> closure recommendation.

## Repository Layout

```text
docs/                  project design, related work, report, and demo script
benchmarks/            local RTL DV benchmarks
jasper/                JasperGold TCL flows and generated reports
tools/                 Jasper runners, parsers, context builders, validators
copilot/               agent stubs, prompts, baselines, JSON schemas
evaluation/            metrics, evaluation runner, result tables
scripts/               convenience scripts
```

## Benchmarks

The primary benchmark is local and DV-focused:

- `arbiter_rr2`: 2-client round-robin arbiter
- `rv_buffer`: single-entry ready/valid buffer
- `apb_regblock`: tiny APB-lite register block

Each benchmark is structured around correct RTL, bug variants, SVA properties, assumptions, coverage goals, manifests, and labeled cases. The current primary benchmark contains 30 labeled DV triage / coverage-closure cases, 10 per design.

## JasperGold Environment

The target server environment provided for this project is:

```bash
ssh moore
source /vol/eecs391/cadence.env
```

Typical remote use:

```bash
ssh moore
cd /path/to/Formal-Aware-AI-DV-Copilot
source /vol/eecs391/cadence.env
python3 tools/run_jasper.py --design arbiter_rr2 --variant correct --mode prove
```

The wrapper expects a JasperGold executable named `jg` by default. Override it with `JASPER_BIN` if needed:

```bash
JASPER_BIN=jaspergold python3 tools/run_jasper.py --design arbiter_rr2 --variant correct --mode prove
```

On `moore`, the default `python3` can be too old for this codebase. Use `python3.11` and the JasperGold binary found under Xcelium 2018:

```bash
source /vol/eecs391/cadence.env
JASPER_BIN=/vol/cadence2018/XCELIUM1809/tools.lnx86/jasper/bin/jg \
  python3.11 tools/run_jasper.py --design arbiter_rr2 --variant correct --mode prove
```

## Initial Commands

Build a structured evidence packet from existing reports:

```bash
python tools/build_evidence_packet.py \
  --case benchmarks/arbiter_rr2/cases/rtl_bug_double_grant.json \
  --out jasper/reports/arbiter_rr2_rtl_bug_double_grant/evidence_packet.json
```

Validate JSON files against the local schemas:

```bash
python tools/validate_json.py copilot/schemas/evidence_packet.schema.json jasper/reports/arbiter_rr2_rtl_bug_double_grant/evidence_packet.json
```

Run the scaffold-level evaluation:

```bash
python evaluation/run_eval.py --cases benchmarks/arbiter_rr2/cases benchmarks/rv_buffer/cases benchmarks/apb_regblock/cases
```

Build evidence packets for all labeled cases:

```bash
python scripts/build_all_evidence_packets.py
```

Run the current formal-aware triage agent scaffold on all 30 cases:

```bash
python evaluation/run_agent_eval.py --out evaluation/results/agent_eval_local.json
```

Run the deterministic baseline comparison without an LLM:

```bash
python evaluation/run_agent_eval.py --all-systems --out evaluation/results/agent_eval_all_local.json
```

Run the structured-packet ablation scaffold:

```bash
python evaluation/run_agent_eval.py \
  --systems structured \
  --ablations no_assertion_manifest no_assumption_manifest no_jasper_cex no_coverage_context minimal_packet \
  --out evaluation/results/agent_eval_ablation_local.json
```

Run SVA generation scaffold evaluation on the local property-intent set:

```bash
python evaluation/run_sva_eval.py --out evaluation/results/sva_eval_local.json
```

Run SVA generation with JasperGold syntax/proof/vacuity re-check:

```bash
python evaluation/run_sva_eval.py --jasper-check --out evaluation/results/sva_eval_jasper_moore.json
```

On `moore`, the convenience script sets the JasperGold binary path:

```bash
source /vol/eecs391/cadence.env
bash scripts/run_moore_sva_eval.sh
```

Run the SVA repair benchmark with injected syntax, signal, reset, and temporal property bugs:

```bash
python evaluation/run_sva_repair_eval.py --out evaluation/results/sva_repair_local.json
```

Run the same repair loop with JasperGold re-check after each candidate:

```bash
python evaluation/run_sva_repair_eval.py --jasper-check --out evaluation/results/sva_repair_jasper_moore.json
```

On `moore`:

```bash
source /vol/eecs391/cadence.env
bash scripts/run_moore_sva_repair_eval.sh
```

The current JasperGold repair result table is tracked in `evaluation/results/sva_repair_results.md`.

Run the coverage-closure benchmark on coverage-only cases:

```bash
python evaluation/run_coverage_eval.py --all-systems --out evaluation/results/coverage_eval_local.json
```

The agent layer is model-agnostic. By default it uses a deterministic structured fallback so the evaluation plumbing can run without a hosted API. To connect an LLM, set `JASPERLOOP_LLM_CMD` to a command that reads the prompt from stdin and writes a JSON object to stdout, or pass `--llm-command`:

```bash
JASPERLOOP_LLM_CMD="python path/to/your_llm_wrapper.py" \
  python evaluation/run_agent_eval.py --all-systems --llm --out evaluation/results/agent_eval_llm.json
```

This repository includes a Codex CLI JSON adapter for local non-interactive experiments. It reads the agent prompt from stdin and writes the final Codex message to stdout:

```bash
JASPERLOOP_LLM_CMD="python copilot/llm_adapters/codex_json.py --schema copilot/schemas/sva_repair_candidate.schema.json --cd ." \
  python evaluation/run_sva_repair_eval.py --llm --out evaluation/results/sva_repair_codex_local.json
```

For a safer opt-in wrapper around Codex CLI experiments, see `docs/codex_cli_usage.md`. The wrapper requires `--acknowledge-external-send` before sending local benchmark content to Codex/OpenAI.
Current Codex CLI smoke-test status is tracked in `evaluation/results/codex_cli_results.md`.
Use `scripts/export_codex_prompts.py --summary-only` to audit prompt size and content categories before any external Codex run.

You can inspect the exact prompt sent to the DV triage agent:

```bash
python copilot/agents/dv_triage_agent.py jasper/reports/case_packets/arbiter_rr2/arbiter_A1/evidence_packet.json --prompt-out /tmp/triage_prompt.txt
```

You can also inspect the raw-log baseline prompt:

```bash
python copilot/baselines/raw_log_llm.py jasper/reports/case_packets/arbiter_rr2/arbiter_A1/evidence_packet.json --prompt-out /tmp/raw_log_prompt.txt
```

For SVA generation prompts:

```bash
python copilot/agents/sva_generation_agent.py benchmarks/sva_generation_cases.json --prompt-out /tmp/sva_generation_prompt.txt
```

## Research Claim

The core claim is not that the LLM is the oracle. JasperGold remains the oracle for syntax, proof, counterexamples, cover reachability, and vacuity. The LLM is constrained by structured formal evidence and used as an assistant for interpretation, repair suggestions, diagnosis, and next actions.

## Planned Evaluation

- SVA generation/repair: `syntax_pass@1`, `syntax_pass_final`, `proven@1`, `proven_final`, `vacuous_rate`, `repair_success_rate`, `average_rounds_to_success`
- Failure triage: `issue_type_accuracy`, `next_action_accuracy`, `top1/top3_root_cause_accuracy`, `evidence_precision`
- Coverage closure: `gap_type_accuracy`, `action_accuracy`, `wrong_test_suggestion_rate`
- Output quality: `valid_json_rate`, `hallucinated_signal_rate`, `unsupported_recommendation_rate`
- LLM integration quality: `source_counts`, `llm_success_rate`, `fallback_rate`, `llm_error_rate`
