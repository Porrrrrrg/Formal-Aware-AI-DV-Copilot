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

Each benchmark is structured around correct RTL, bug variants, SVA properties, assumptions, coverage goals, manifests, and labeled cases.

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

## Research Claim

The core claim is not that the LLM is the oracle. JasperGold remains the oracle for syntax, proof, counterexamples, cover reachability, and vacuity. The LLM is constrained by structured formal evidence and used as an assistant for interpretation, repair suggestions, diagnosis, and next actions.

## Planned Evaluation

- SVA generation/repair: `syntax_pass@1`, `syntax_pass_final`, `proven@1`, `proven_final`, `vacuous_rate`, `repair_success_rate`, `average_rounds_to_success`
- Failure triage: `issue_type_accuracy`, `next_action_accuracy`, `top1/top3_root_cause_accuracy`, `evidence_precision`
- Coverage closure: `gap_type_accuracy`, `action_accuracy`, `wrong_test_suggestion_rate`
- Output quality: `valid_json_rate`, `hallucinated_signal_rate`, `unsupported_recommendation_rate`
